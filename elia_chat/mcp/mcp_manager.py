"""MCP manager for coordinating multiple MCP clients and tool execution."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set, Callable
from collections import defaultdict
from datetime import datetime, timedelta

from elia_chat.mcp.mcp_client import MCPClient, MCPConnectionStatus
from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.exceptions import (
    MCPError, MCPConnectionError, MCPToolError, MCPServerError, 
    MCPErrorCode, handle_mcp_error, create_graceful_degradation_error
)
from elia_chat.mcp.logging_config import get_mcp_logger

logger = logging.getLogger(__name__)





class ServerStatusInfo:
    """Information about an MCP server's status and metrics."""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.connection_attempts = 0
        self.successful_connections = 0
        self.last_connection_time: Optional[datetime] = None
        self.last_disconnection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None
        self.tool_call_count = 0
        self.failed_tool_calls = 0
        self.total_tool_execution_time = 0.0
        self.uptime_start: Optional[datetime] = None
        
    def record_connection_attempt(self) -> None:
        """Record a connection attempt."""
        self.connection_attempts += 1
        
    def record_successful_connection(self) -> None:
        """Record a successful connection."""
        self.successful_connections += 1
        self.last_connection_time = datetime.now()
        self.uptime_start = datetime.now()
        self.last_error = None
        self.last_error_time = None
        
    def record_disconnection(self) -> None:
        """Record a disconnection."""
        self.last_disconnection_time = datetime.now()
        self.uptime_start = None
        
    def record_error(self, error: str) -> None:
        """Record an error."""
        self.last_error = error
        self.last_error_time = datetime.now()
        
    def record_tool_call(self, execution_time: float, success: bool = True) -> None:
        """Record a tool call execution."""
        self.tool_call_count += 1
        self.total_tool_execution_time += execution_time
        if not success:
            self.failed_tool_calls += 1
            
    @property
    def connection_success_rate(self) -> float:
        """Get connection success rate as a percentage."""
        if self.connection_attempts == 0:
            return 0.0
        return (self.successful_connections / self.connection_attempts) * 100
        
    @property
    def tool_success_rate(self) -> float:
        """Get tool call success rate as a percentage."""
        if self.tool_call_count == 0:
            return 0.0
        successful_calls = self.tool_call_count - self.failed_tool_calls
        return (successful_calls / self.tool_call_count) * 100
        
    @property
    def average_tool_execution_time(self) -> float:
        """Get average tool execution time in seconds."""
        if self.tool_call_count == 0:
            return 0.0
        return self.total_tool_execution_time / self.tool_call_count
        
    @property
    def uptime(self) -> Optional[timedelta]:
        """Get current uptime if connected."""
        if self.uptime_start is None:
            return None
        return datetime.now() - self.uptime_start
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert status info to dictionary."""
        return {
            "server_name": self.server_name,
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "connection_success_rate": self.connection_success_rate,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "last_disconnection_time": self.last_disconnection_time.isoformat() if self.last_disconnection_time else None,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "tool_call_count": self.tool_call_count,
            "failed_tool_calls": self.failed_tool_calls,
            "tool_success_rate": self.tool_success_rate,
            "average_tool_execution_time": self.average_tool_execution_time,
            "uptime_seconds": self.uptime.total_seconds() if self.uptime else None
        }


class MCPManager:
    """Manages multiple MCP clients and coordinates tool execution."""
    
    def __init__(self, config: MCPConfig):
        """Initialize MCP manager.
        
        Args:
            config: MCP configuration containing server definitions
        """
        self.config = config
        self.clients: Dict[str, MCPClient] = {}
        self._tool_to_server: Dict[str, str] = {}
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        self._server_status: Dict[str, ServerStatusInfo] = {}
        self._status_change_callbacks: List[Callable[[str, MCPConnectionStatus], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._mcp_logger = get_mcp_logger()
        
    async def initialize(self) -> None:
        """Initialize all configured MCP clients."""
        logger.info("Initializing MCP manager")
        
        enabled_servers = self.config.get_enabled_servers()
        if not enabled_servers:
            logger.info("No enabled MCP servers found in configuration")
            return
        
        # Create clients for all enabled servers
        for server_name, server_config in enabled_servers.items():
            client = MCPClient(server_name, server_config)
            self.clients[server_name] = client
            self._server_status[server_name] = ServerStatusInfo(server_name)
            
        # Connect to all servers concurrently
        connection_tasks = [
            self._connect_client(server_name, client)
            for server_name, client in self.clients.items()
        ]
        
        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Build tool routing table
        await self._rebuild_tool_routing()
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(f"MCP manager initialized with {len(self.clients)} servers")
        
        # Log manager initialization
        self._mcp_logger.log_security_event(
            event="MCP manager initialized",
            severity="INFO",
            details={
                "total_servers": len(self.clients),
                "enabled_servers": list(enabled_servers.keys()),
                "connected_servers": self.get_connected_servers()
            }
        )
    
    async def shutdown(self) -> None:
        """Shutdown all MCP clients and cleanup resources."""
        logger.info("Shutting down MCP manager")
        
        # Signal shutdown to stop reconnection tasks
        self._shutdown_event.set()
        
        # Cancel monitoring task
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        
        # Cancel all reconnection tasks
        for task in self._reconnect_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        tasks_to_wait = list(self._reconnect_tasks.values())
        if self._monitoring_task:
            tasks_to_wait.append(self._monitoring_task)
        
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)
        
        # Disconnect all clients
        disconnect_tasks = [
            client.disconnect()
            for client in self.clients.values()
        ]
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        # Clear state
        self.clients.clear()
        self._tool_to_server.clear()
        self._reconnect_tasks.clear()
        self._server_status.clear()
        self._status_change_callbacks.clear()
        
        logger.info("MCP manager shutdown complete")
    
    async def _connect_client(self, server_name: str, client: MCPClient) -> None:
        """Connect a single MCP client with error handling.
        
        Args:
            server_name: Name of the server
            client: MCP client instance
        """
        status_info = self._server_status.get(server_name)
        if status_info:
            status_info.record_connection_attempt()
        
        try:
            success = await client.connect()
            if success:
                logger.info(f"Successfully connected to MCP server '{server_name}'")
                if status_info:
                    status_info.record_successful_connection()
                self._notify_status_change(server_name, client.status)
            else:
                logger.warning(f"Failed to connect to MCP server '{server_name}'")
                if status_info and client.connection_error:
                    status_info.record_error(client.connection_error)
                # Start reconnection task for failed connections
                await self._start_reconnection_task(server_name, client)
        except Exception as e:
            logger.error(f"Error connecting to MCP server '{server_name}': {e}")
            if status_info:
                status_info.record_error(str(e))
            await self._start_reconnection_task(server_name, client)
    
    async def _start_reconnection_task(self, server_name: str, client: MCPClient) -> None:
        """Start automatic reconnection task for a failed client.
        
        Args:
            server_name: Name of the server
            client: MCP client instance
        """
        if server_name in self._reconnect_tasks:
            # Cancel existing reconnection task
            self._reconnect_tasks[server_name].cancel()
        
        # Start new reconnection task
        self._reconnect_tasks[server_name] = asyncio.create_task(
            self._reconnection_loop(server_name, client)
        )
    
    async def _reconnection_loop(self, server_name: str, client: MCPClient) -> None:
        """Automatic reconnection loop for a failed MCP client.
        
        Args:
            server_name: Name of the server
            client: MCP client instance
        """
        retry_delays = [1, 2, 5, 10, 30, 60]  # Exponential backoff
        retry_index = 0
        
        while not self._shutdown_event.is_set():
            try:
                # Wait before retry
                delay = retry_delays[min(retry_index, len(retry_delays) - 1)]
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=delay
                )
                # If we reach here, shutdown was signaled
                break
                
            except asyncio.TimeoutError:
                # Timeout is expected, continue with reconnection attempt
                pass
            
            try:
                logger.debug(f"Attempting to reconnect to MCP server '{server_name}'")
                success = await client.connect()
                
                if success:
                    logger.info(f"Successfully reconnected to MCP server '{server_name}'")
                    # Update status tracking
                    status_info = self._server_status.get(server_name)
                    if status_info:
                        status_info.record_successful_connection()
                    # Notify status change
                    self._notify_status_change(server_name, client.status)
                    # Rebuild tool routing to include this server's tools
                    await self._rebuild_tool_routing()
                    break
                else:
                    retry_index += 1
                    logger.debug(f"Reconnection attempt {retry_index} failed for server '{server_name}'")
                    
            except Exception as e:
                retry_index += 1
                logger.debug(f"Reconnection error for server '{server_name}': {e}")
        
        # Clean up the task reference
        if server_name in self._reconnect_tasks:
            del self._reconnect_tasks[server_name]
    
    async def _rebuild_tool_routing(self) -> None:
        """Rebuild the tool-to-server routing table."""
        self._tool_to_server.clear()
        
        for server_name, client in self.clients.items():
            if client.is_connected:
                try:
                    tools = await client.list_tools()
                    for tool in tools:
                        tool_name = tool["function"]["name"]
                        
                        # Handle tool name conflicts
                        if tool_name in self._tool_to_server:
                            existing_server = self._tool_to_server[tool_name]
                            logger.warning(
                                f"Tool name conflict: '{tool_name}' exists on both "
                                f"'{existing_server}' and '{server_name}'. "
                                f"Using '{existing_server}'"
                            )
                        else:
                            self._tool_to_server[tool_name] = server_name
                            
                except Exception as e:
                    logger.error(f"Failed to list tools from server '{server_name}': {e}")
        
        logger.debug(f"Tool routing table rebuilt with {len(self._tool_to_server)} tools")
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all connected servers.
        
        Returns:
            List of tool definitions in LiteLLM-compatible format
        """
        all_tools = []
        seen_tools = set()
        
        for server_name, client in self.clients.items():
            if client.is_connected:
                try:
                    tools = await client.list_tools()
                    for tool in tools:
                        tool_name = tool["function"]["name"]
                        
                        # Avoid duplicate tools (first server wins)
                        if tool_name not in seen_tools:
                            seen_tools.add(tool_name)
                            # Add server metadata to tool definition
                            tool_with_metadata = tool.copy()
                            tool_with_metadata["_mcp_server"] = server_name
                            all_tools.append(tool_with_metadata)
                        
                except Exception as e:
                    logger.error(f"Failed to get tools from server '{server_name}': {e}")
        
        return all_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool, finding the appropriate server.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool is not found or execution fails
            MCPServerError: If server is not available
        """
        # Find the server that provides this tool
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            available_tools = list(self._tool_to_server.keys())
            raise MCPToolError(
                message=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
                error_code=MCPErrorCode.TOOL_NOT_FOUND,
                details={"available_tools": available_tools}
            )
        
        # Get the client for this server
        client = self.clients.get(server_name)
        if not client:
            raise MCPServerError(
                message=f"Server '{server_name}' not found in manager",
                server_name=server_name,
                error_code=MCPErrorCode.SERVER_NOT_FOUND
            )
        
        if not client.is_connected:
            # Try to reconnect if not already attempting
            if server_name not in self._reconnect_tasks:
                logger.info(f"Attempting to reconnect to server '{server_name}' for tool '{tool_name}'")
                await self._start_reconnection_task(server_name, client)
            
            raise MCPConnectionError(
                message=f"Server '{server_name}' is not connected",
                server_name=server_name,
                tool_name=tool_name,
                error_code=MCPErrorCode.SERVER_UNAVAILABLE
            )
        
        # Record tool execution metrics
        start_time = time.time()
        status_info = self._server_status.get(server_name)
        
        try:
            result = await client.call_tool(tool_name, arguments)
            execution_time = time.time() - start_time
            if status_info:
                status_info.record_tool_call(execution_time, success=True)
            
            logger.debug(f"Tool '{tool_name}' executed successfully via server '{server_name}' in {execution_time:.2f}s")
            return result
            
        except MCPError as e:
            execution_time = time.time() - start_time
            if status_info:
                status_info.record_tool_call(execution_time, success=False)
                status_info.record_error(str(e))
            
            # Add manager context to the error
            e.details = e.details or {}
            e.details.update({
                "manager_context": "tool_execution",
                "execution_time": execution_time
            })
            
            logger.error(f"Tool '{tool_name}' execution failed on server '{server_name}': {e}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            if status_info:
                status_info.record_tool_call(execution_time, success=False)
                status_info.record_error(str(e))
            
            # Convert unexpected errors to MCP errors
            mcp_error = handle_mcp_error(
                error=e,
                operation=f"Tool '{tool_name}' execution via manager",
                server_name=server_name,
                tool_name=tool_name,
                default_error_code=MCPErrorCode.TOOL_EXECUTION_FAILED
            )
            
            mcp_error.details = mcp_error.details or {}
            mcp_error.details.update({
                "manager_context": "tool_execution",
                "execution_time": execution_time
            })
            
            logger.error(f"Unexpected error during tool '{tool_name}' execution: {mcp_error}")
            raise mcp_error
    
    async def is_tool_auto_approved(self, tool_name: str) -> bool:
        """Check if a tool is in the auto-approve list for its server.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool is auto-approved, False otherwise
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return False
        
        client = self.clients.get(server_name)
        if not client:
            return False
        
        return client.is_tool_auto_approved(tool_name)
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all MCP servers.
        
        Returns:
            Dictionary mapping server names to their status information
        """
        status = {}
        
        for server_name, client in self.clients.items():
            status[server_name] = {
                "status": client.status.value,
                "connected": client.is_connected,
                "error": client.connection_error,
                "tool_count": len(client._tools) if client.is_connected else 0,
                "auto_approve_count": len(client.config.auto_approve),
                "timeout": client.config.timeout
            }
        
        return status
    
    async def handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle multiple tool calls from language model.
        
        Args:
            tool_calls: List of tool call requests from the language model
            
        Returns:
            List of tool call results
        """
        results = []
        
        # Execute tool calls concurrently where possible
        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            arguments = tool_call.get("function", {}).get("arguments", {})
            call_id = tool_call.get("id", "")
            
            if not tool_name:
                results.append({
                    "tool_call_id": call_id,
                    "role": "tool",
                    "name": tool_name or "unknown",
                    "content": "Error: Missing tool name in tool call"
                })
                continue
            
            # Create task for this tool call
            task = asyncio.create_task(
                self._execute_single_tool_call(call_id, tool_name, arguments)
            )
            tasks.append(task)
        
        # Wait for all tool calls to complete
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(task_results)
        
        return results
    
    async def _execute_single_tool_call(
        self, 
        call_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single tool call and format the result.
        
        Args:
            call_id: Tool call ID from the language model
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Formatted tool call result
        """
        try:
            result = await self.execute_tool(tool_name, arguments)
            
            return {
                "tool_call_id": call_id,
                "role": "tool",
                "name": tool_name,
                "content": result.get("content", "")
            }
            
        except Exception as e:
            logger.error(f"Tool call failed for '{tool_name}': {e}")
            
            return {
                "tool_call_id": call_id,
                "role": "tool", 
                "name": tool_name,
                "content": f"Error: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all MCP clients.
        
        Returns:
            Dictionary mapping server names to their health status
        """
        health_status = {}
        
        # Run health checks concurrently
        tasks = []
        server_names = []
        
        for server_name, client in self.clients.items():
            tasks.append(client.health_check())
            server_names.append(server_name)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for server_name, result in zip(server_names, results):
                if isinstance(result, Exception):
                    health_status[server_name] = False
                    logger.error(f"Health check failed for server '{server_name}': {result}")
                else:
                    health_status[server_name] = result
                    
                    # Start reconnection if health check failed
                    if not result and server_name not in self._reconnect_tasks:
                        client = self.clients[server_name]
                        await self._start_reconnection_task(server_name, client)
        
        return health_status
    
    def get_tool_server(self, tool_name: str) -> Optional[str]:
        """Get the server name that provides a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Server name or None if tool not found
        """
        return self._tool_to_server.get(tool_name)
    
    def get_connected_servers(self) -> List[str]:
        """Get list of currently connected server names.
        
        Returns:
            List of connected server names
        """
        return [
            server_name 
            for server_name, client in self.clients.items()
            if client.is_connected
        ]
    
    def get_total_tool_count(self) -> int:
        """Get total number of available tools across all servers.
        
        Returns:
            Total tool count
        """
        return len(self._tool_to_server)
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for server health and status."""
        health_check_interval = 60  # Check every 60 seconds
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for the next health check or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=health_check_interval
                )
                # If we reach here, shutdown was signaled
                break
                
            except asyncio.TimeoutError:
                # Timeout is expected, perform health check
                pass
            
            try:
                # Perform health checks on all clients
                await self.health_check()
                
                # Log status summary
                connected_servers = self.get_connected_servers()
                total_servers = len(self.clients)
                logger.debug(
                    f"MCP status check: {len(connected_servers)}/{total_servers} "
                    f"servers connected, {self.get_total_tool_count()} tools available"
                )
                
            except Exception as e:
                logger.error(f"Error in MCP monitoring loop: {e}")
    
    def _notify_status_change(self, server_name: str, status: MCPConnectionStatus) -> None:
        """Notify registered callbacks about status changes.
        
        Args:
            server_name: Name of the server
            status: New connection status
        """
        for callback in self._status_change_callbacks:
            try:
                callback(server_name, status)
            except Exception as e:
                logger.error(f"Error in status change callback: {e}")
    
    def add_status_change_callback(self, callback: Callable[[str, MCPConnectionStatus], None]) -> None:
        """Add a callback for server status changes.
        
        Args:
            callback: Function to call when server status changes.
                     Receives (server_name, new_status) as arguments.
        """
        self._status_change_callbacks.append(callback)
    
    def remove_status_change_callback(self, callback: Callable[[str, MCPConnectionStatus], None]) -> None:
        """Remove a status change callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._status_change_callbacks:
            self._status_change_callbacks.remove(callback)
    
    def get_server_metrics(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed metrics for a specific server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server metrics dictionary or None if server not found
        """
        status_info = self._server_status.get(server_name)
        if not status_info:
            return None
        
        client = self.clients.get(server_name)
        base_metrics = status_info.to_dict()
        
        if client:
            base_metrics.update({
                "current_status": client.status.value,
                "is_connected": client.is_connected,
                "current_error": client.connection_error,
                "tool_count": len(client._tools) if hasattr(client, '_tools') else 0,
                "auto_approve_tools": client.config.auto_approve,
                "timeout": client.config.timeout
            })
        
        return base_metrics
    
    def get_all_server_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed metrics for all servers.
        
        Returns:
            Dictionary mapping server names to their metrics
        """
        metrics = {}
        for server_name in self._server_status:
            server_metrics = self.get_server_metrics(server_name)
            if server_metrics:
                metrics[server_name] = server_metrics
        return metrics
    
    def get_manager_summary(self) -> Dict[str, Any]:
        """Get a summary of the MCP manager status.
        
        Returns:
            Summary dictionary with overall statistics
        """
        connected_servers = self.get_connected_servers()
        total_servers = len(self.clients)
        total_tools = self.get_total_tool_count()
        
        # Calculate aggregate metrics
        total_tool_calls = sum(
            status.tool_call_count 
            for status in self._server_status.values()
        )
        total_failed_calls = sum(
            status.failed_tool_calls 
            for status in self._server_status.values()
        )
        
        overall_success_rate = 0.0
        if total_tool_calls > 0:
            successful_calls = total_tool_calls - total_failed_calls
            overall_success_rate = (successful_calls / total_tool_calls) * 100
        
        return {
            "connected_servers": len(connected_servers),
            "total_servers": total_servers,
            "connection_rate": (len(connected_servers) / total_servers * 100) if total_servers > 0 else 0,
            "total_tools": total_tools,
            "total_tool_calls": total_tool_calls,
            "failed_tool_calls": total_failed_calls,
            "tool_success_rate": overall_success_rate,
            "connected_server_names": connected_servers,
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done()
        }
    
    def get_monitoring_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring data for MCP operations."""
        return {
            "manager_summary": self.get_manager_summary(),
            "server_metrics": self.get_all_server_metrics(),
            "performance_summary": self._mcp_logger.get_performance_summary(),
            "recent_audit_trail": self._mcp_logger.get_audit_trail(hours=1),
            "health_status": asyncio.create_task(self.health_check()) if not self._shutdown_event.is_set() else None
        }
    
    def cleanup_old_logs(self, days: int = 30) -> Dict[str, int]:
        """Clean up old log entries and return cleanup statistics."""
        cleared_audit = self._mcp_logger.clear_old_entries(days)
        
        # Clean up old server status entries
        cutoff_time = datetime.now() - timedelta(days=days)
        cleared_status = 0
        
        for status_info in self._server_status.values():
            # Reset old error information
            if (status_info.last_error_time and 
                status_info.last_error_time < cutoff_time):
                status_info.last_error = None
                status_info.last_error_time = None
                cleared_status += 1
        
        return {
            "cleared_audit_entries": cleared_audit,
            "cleared_status_entries": cleared_status,
            "cleanup_date": datetime.now().isoformat()
        }
    
    def __repr__(self) -> str:
        """String representation of the MCP manager."""
        connected_count = len(self.get_connected_servers())
        total_count = len(self.clients)
        tool_count = self.get_total_tool_count()
        
        return (
            f"MCPManager(servers={connected_count}/{total_count}, "
            f"tools={tool_count})"
        )