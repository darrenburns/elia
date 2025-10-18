"""MCP client for connecting to and communicating with MCP servers."""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, AsyncGenerator
from enum import Enum

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from elia_chat.mcp.mcp_config import MCPServerConfig
from elia_chat.mcp.exceptions import (
    MCPError, MCPConnectionError, MCPToolError, MCPTimeoutError, 
    MCPProtocolError, MCPErrorCode, handle_mcp_error
)
from elia_chat.mcp.logging_config import get_mcp_logger

logger = logging.getLogger(__name__)


class MCPConnectionStatus(Enum):
    """MCP client connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPClient:
    """Client for connecting to and communicating with MCP servers."""
    
    def __init__(self, server_name: str, config: MCPServerConfig):
        """Initialize MCP client.
        
        Args:
            server_name: Name of the MCP server
            config: Server configuration
        """
        self.server_name = server_name
        self.config = config
        self._session: Optional[ClientSession] = None
        self._status = MCPConnectionStatus.DISCONNECTED
        self._tools: List[Dict[str, Any]] = []
        self._connection_error: Optional[str] = None
        self._mcp_logger = get_mcp_logger()
        
    @property
    def status(self) -> MCPConnectionStatus:
        """Get current connection status."""
        return self._status
    
    @property
    def connection_error(self) -> Optional[str]:
        """Get last connection error message."""
        return self._connection_error
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._status == MCPConnectionStatus.CONNECTED
    
    async def connect(self) -> bool:
        """Establish connection to MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self._status == MCPConnectionStatus.CONNECTED:
            return True
            
        self._status = MCPConnectionStatus.CONNECTING
        self._connection_error = None
        
        try:
            # Validate configuration before attempting connection
            if not self.config.command:
                raise MCPConnectionError(
                    message="Missing command in server configuration",
                    server_name=self.server_name,
                    error_code=MCPErrorCode.INVALID_CONFIG
                )
            
            # Create server parameters for stdio transport
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )
            
            # Create stdio client session with timeout
            try:
                async with asyncio.timeout(self.config.timeout):
                    async with stdio_client(server_params) as (read, write):
                        self._session = ClientSession(read, write)
                        
                        # Initialize the session
                        await self._session.initialize()
                        
                        # List available tools
                        await self._refresh_tools()
                        
                        self._status = MCPConnectionStatus.CONNECTED
                        logger.info(f"Successfully connected to MCP server '{self.server_name}'")
                        
                        # Log connection success
                        self._mcp_logger.log_connection_event(
                            server_name=self.server_name,
                            event="connected",
                            success=True,
                            details={
                                "command": self.config.command,
                                "args": self.config.args,
                                "timeout": self.config.timeout,
                                "tool_count": len(self._tools)
                            }
                        )
                        
                        return True
                        
            except asyncio.TimeoutError:
                raise MCPTimeoutError(
                    message=f"Connection to MCP server '{self.server_name}' timed out",
                    server_name=self.server_name,
                    timeout_duration=self.config.timeout,
                    operation="connection"
                )
                
        except MCPError:
            # Re-raise MCP errors as-is
            raise
        except Exception as e:
            # Convert other exceptions to MCP errors
            mcp_error = handle_mcp_error(
                error=e,
                operation=f"Connection to server '{self.server_name}'",
                server_name=self.server_name,
                default_error_code=MCPErrorCode.CONNECTION_FAILED
            )
            
            # Log the error and update status
            logger.error(f"Failed to connect to MCP server '{self.server_name}': {mcp_error}")
            self._connection_error = mcp_error.user_message
            self._status = MCPConnectionStatus.ERROR
            
            # Log connection failure
            self._mcp_logger.log_connection_event(
                server_name=self.server_name,
                event="connection_failed",
                success=False,
                error=mcp_error.error_code.value if hasattr(mcp_error, 'error_code') else "unknown",
                details={
                    "error_message": str(mcp_error),
                    "user_message": mcp_error.user_message,
                    "command": self.config.command,
                    "args": self.config.args
                }
            )
            
            # Don't re-raise here, return False for graceful degradation
            return False
    
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if self._session:
            try:
                # Close the session if it has a close method
                if hasattr(self._session, 'close'):
                    await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing MCP session for '{self.server_name}': {e}")
            finally:
                self._session = None
                
        self._status = MCPConnectionStatus.DISCONNECTED
        self._tools = []
        logger.info(f"Disconnected from MCP server '{self.server_name}'")
        
        # Log disconnection
        self._mcp_logger.log_connection_event(
            server_name=self.server_name,
            event="disconnected",
            success=True
        )
    
    async def _refresh_tools(self) -> None:
        """Refresh the list of available tools from the server."""
        if not self._session:
            raise MCPConnectionError(
                message="Cannot refresh tools: not connected to MCP server",
                server_name=self.server_name,
                error_code=MCPErrorCode.CONNECTION_LOST
            )
            
        try:
            # List tools from the server with timeout
            result = await asyncio.wait_for(
                self._session.list_tools(),
                timeout=self.config.timeout
            )
            
            # Validate the response
            if not hasattr(result, 'tools'):
                raise MCPProtocolError(
                    message=f"Invalid tools response from server '{self.server_name}': missing 'tools' field",
                    server_name=self.server_name,
                    error_code=MCPErrorCode.INVALID_RESPONSE
                )
            
            # Convert MCP tool format to LiteLLM-compatible format
            self._tools = []
            for tool in result.tools:
                try:
                    # Validate tool structure
                    if not hasattr(tool, 'name') or not tool.name:
                        logger.warning(f"Skipping tool with missing name from server '{self.server_name}'")
                        continue
                    
                    tool_def = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema or {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                    self._tools.append(tool_def)
                    
                except Exception as tool_error:
                    logger.warning(
                        f"Skipping invalid tool from server '{self.server_name}': {tool_error}"
                    )
                    continue
                
            logger.debug(f"Loaded {len(self._tools)} tools from MCP server '{self.server_name}'")
            
        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message=f"Tool listing timed out for server '{self.server_name}'",
                server_name=self.server_name,
                timeout_duration=self.config.timeout,
                operation="list_tools"
            )
        except MCPError:
            # Re-raise MCP errors as-is
            raise
        except Exception as e:
            # Convert other exceptions to MCP errors
            raise handle_mcp_error(
                error=e,
                operation=f"Tool listing from server '{self.server_name}'",
                server_name=self.server_name,
                default_error_code=MCPErrorCode.PROTOCOL_ERROR
            )
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server.
        
        Returns:
            List of tool definitions in LiteLLM-compatible format
            
        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.is_connected:
            raise MCPConnectionError(
                message=f"Cannot list tools: not connected to MCP server '{self.server_name}'",
                server_name=self.server_name,
                error_code=MCPErrorCode.CONNECTION_LOST
            )
            
        return self._tools.copy()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPConnectionError: If not connected to server
            MCPToolError: If tool execution fails
        """
        if not self.is_connected or not self._session:
            raise MCPConnectionError(
                message=f"Cannot execute tool: not connected to MCP server '{self.server_name}'",
                server_name=self.server_name,
                tool_name=tool_name,
                error_code=MCPErrorCode.CONNECTION_LOST
            )
        
        # Validate that the tool exists
        tool_names = [tool["function"]["name"] for tool in self._tools]
        if tool_name not in tool_names:
            raise MCPToolError(
                message=f"Tool '{tool_name}' not found on server '{self.server_name}'",
                tool_name=tool_name,
                server_name=self.server_name,
                error_code=MCPErrorCode.TOOL_NOT_FOUND,
                details={"available_tools": tool_names}
            )
        
        # Validate arguments against tool schema
        try:
            self._validate_tool_arguments(tool_name, arguments)
        except ValueError as e:
            raise MCPToolError(
                message=f"Invalid arguments for tool '{tool_name}': {e}",
                tool_name=tool_name,
                server_name=self.server_name,
                error_code=MCPErrorCode.INVALID_ARGUMENTS,
                details={"provided_arguments": arguments}
            )
        
        # Record start time for performance monitoring
        start_time = time.time()
        
        try:
            # Execute the tool with timeout and performance monitoring
            with self._mcp_logger.time_operation(f"tool_execution_{tool_name}", self.server_name):
                result = await asyncio.wait_for(
                    self._session.call_tool(tool_name, arguments),
                    timeout=self.config.timeout
                )
            
            # Validate and format the result
            if hasattr(result, 'isError') and result.isError:
                error_content = str(result.content) if hasattr(result, 'content') else "Unknown error"
                
                # Log failed tool execution
                execution_time_ms = (time.time() - start_time) * 1000
                self._mcp_logger.log_tool_execution(
                    server_name=self.server_name,
                    tool_name=tool_name,
                    duration_ms=execution_time_ms,
                    success=False,
                    error="server_error",
                    arguments=arguments
                )
                
                raise MCPToolError(
                    message=f"Tool '{tool_name}' returned error: {error_content}",
                    tool_name=tool_name,
                    server_name=self.server_name,
                    error_code=MCPErrorCode.TOOL_EXECUTION_FAILED,
                    details={"server_error": error_content}
                )
            
            # Extract content from result
            content = self._extract_result_content(result)
            
            # Calculate execution metrics
            execution_time_ms = (time.time() - start_time) * 1000
            result_size = len(content) if content else 0
            
            # Log successful tool execution
            self._mcp_logger.log_tool_execution(
                server_name=self.server_name,
                tool_name=tool_name,
                duration_ms=execution_time_ms,
                success=True,
                arguments=arguments,
                result_size=result_size
            )
            
            logger.debug(f"Tool '{tool_name}' executed successfully on server '{self.server_name}' in {execution_time_ms:.2f}ms")
            
            return {
                "success": True,
                "content": content,
                "tool_name": tool_name,
                "server_name": self.server_name
            }
            
        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log timeout
            self._mcp_logger.log_tool_execution(
                server_name=self.server_name,
                tool_name=tool_name,
                duration_ms=execution_time_ms,
                success=False,
                error="timeout",
                arguments=arguments
            )
            
            raise MCPTimeoutError(
                message=f"Tool '{tool_name}' execution timed out",
                tool_name=tool_name,
                server_name=self.server_name,
                timeout_duration=self.config.timeout,
                operation="tool_execution"
            )
        except MCPError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log MCP error
            self._mcp_logger.log_tool_execution(
                server_name=self.server_name,
                tool_name=tool_name,
                duration_ms=execution_time_ms,
                success=False,
                error=e.error_code.value if hasattr(e, 'error_code') else "mcp_error",
                arguments=arguments
            )
            
            # Re-raise MCP errors as-is
            raise
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log unexpected error
            self._mcp_logger.log_tool_execution(
                server_name=self.server_name,
                tool_name=tool_name,
                duration_ms=execution_time_ms,
                success=False,
                error="unexpected_error",
                arguments=arguments
            )
            
            # Convert other exceptions to MCP errors
            raise handle_mcp_error(
                error=e,
                operation=f"Tool '{tool_name}' execution on server '{self.server_name}'",
                server_name=self.server_name,
                tool_name=tool_name,
                default_error_code=MCPErrorCode.TOOL_EXECUTION_FAILED
            )
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition or None if not found
        """
        for tool in self._tools:
            if tool["function"]["name"] == tool_name:
                return tool
        return None
    
    def is_tool_auto_approved(self, tool_name: str) -> bool:
        """Check if a tool is in the auto-approve list.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool is auto-approved, False otherwise
        """
        is_approved = tool_name in self.config.auto_approve
        
        # Log security event for tool approval check
        self._mcp_logger.log_security_event(
            event=f"Tool approval check: {'approved' if is_approved else 'requires_approval'}",
            server_name=self.server_name,
            tool_name=tool_name,
            severity="INFO",
            details={
                "auto_approved": is_approved,
                "auto_approve_list": self.config.auto_approve
            }
        )
        
        return is_approved
    
    async def health_check(self) -> bool:
        """Perform a health check on the connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_connected or not self._session:
            return False
            
        try:
            # Try to list tools as a health check
            await self._session.list_tools()
            return True
        except Exception as e:
            logger.warning(f"Health check failed for MCP server '{self.server_name}': {e}")
            self._status = MCPConnectionStatus.ERROR
            self._connection_error = str(e)
            return False
    
    def _validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments against the tool's schema.
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
        """
        tool_def = self.get_tool_by_name(tool_name)
        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        parameters = tool_def["function"].get("parameters", {})
        required_params = parameters.get("required", [])
        properties = parameters.get("properties", {})
        
        # Check required parameters
        for param in required_params:
            if param not in arguments:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Check for unknown parameters
        for param in arguments:
            if param not in properties:
                logger.warning(f"Unknown parameter '{param}' for tool '{tool_name}'")
    
    def _extract_result_content(self, result) -> str:
        """Extract content from MCP tool result.
        
        Args:
            result: MCP tool execution result
            
        Returns:
            Extracted content as string
        """
        content = ""
        
        if hasattr(result, 'content') and result.content:
            if isinstance(result.content, list):
                # Handle multiple content items
                content_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_parts.append(item.text)
                    elif isinstance(item, dict) and 'text' in item:
                        content_parts.append(item['text'])
                    else:
                        content_parts.append(str(item))
                content = "\n".join(content_parts)
            else:
                content = str(result.content)
        
        return content
    
    def __repr__(self) -> str:
        """String representation of the MCP client."""
        return f"MCPClient(server='{self.server_name}', status={self.status.value}, tools={len(self._tools)})"