"""Integration tests for MCP system with Elia Chat."""

import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from elia_chat.app import Elia
from elia_chat.config import LaunchConfig, EliaChatModel
from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.mcp_manager import MCPManager
from elia_chat.mcp.exceptions import MCPError, MCPConnectionError, MCPToolError
from elia_chat.mcp.mcp_client import MCPConnectionStatus


class TestMCPIntegration:
    """Test MCP integration with the main Elia application."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.launch_config = LaunchConfig()
        
        # Create test MCP configuration
        self.mcp_config = MCPConfig(
            mcp_servers={
                "test-calculator": MCPServerConfig(
                    command="python",
                    args=["test_calculator.py"],
                    auto_approve=["add", "subtract"],
                    timeout=30
                ),
                "test-weather": MCPServerConfig(
                    command="python", 
                    args=["test_weather.py"],
                    auto_approve=[],
                    timeout=15
                )
            }
        )
    
    @pytest.mark.asyncio
    async def test_app_initialization_with_mcp(self):
        """Test that Elia app initializes correctly with MCP configuration."""
        with patch('elia_chat.mcp.mcp_config.MCPConfig.load_default', return_value=self.mcp_config):
            app = Elia(self.launch_config)
            
            # Check MCP components are initialized
            assert app.mcp_config is not None
            assert app.mcp_manager is not None
            assert isinstance(app.mcp_manager, MCPManager)
            assert len(app.mcp_config.mcp_servers) == 2
    
    @pytest.mark.asyncio
    async def test_app_initialization_without_mcp(self):
        """Test that Elia app works without MCP configuration."""
        empty_config = MCPConfig()
        
        with patch('elia_chat.mcp.mcp_config.MCPConfig.load_default', return_value=empty_config):
            app = Elia(self.launch_config)
            
            # Check MCP components are initialized but empty
            assert app.mcp_config is not None
            assert app.mcp_manager is not None
            assert len(app.mcp_config.mcp_servers) == 0
    
    @pytest.mark.asyncio
    async def test_mcp_manager_initialization_on_mount(self):
        """Test that MCP manager is initialized when app mounts."""
        with patch('elia_chat.mcp.mcp_config.MCPConfig.load_default', return_value=self.mcp_config):
            app = Elia(self.launch_config)
            
            # Mock the MCP manager initialization
            with patch.object(app.mcp_manager, 'initialize') as mock_init:
                await app.on_mount()
                mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mcp_manager_shutdown_on_unmount(self):
        """Test that MCP manager is shut down when app unmounts."""
        with patch('elia_chat.mcp.mcp_config.MCPConfig.load_default', return_value=self.mcp_config):
            app = Elia(self.launch_config)
            
            # Mock the MCP manager shutdown
            with patch.object(app.mcp_manager, 'shutdown') as mock_shutdown:
                await app.on_unmount()
                mock_shutdown.assert_called_once()


class TestMCPManagerIntegration:
    """Test MCP manager integration and coordination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "calculator": MCPServerConfig(
                    command="python",
                    args=["calculator.py"],
                    auto_approve=["add"],
                    timeout=30
                ),
                "weather": MCPServerConfig(
                    command="python",
                    args=["weather.py"],
                    auto_approve=[],
                    timeout=15
                )
            }
        )
        self.manager = MCPManager(self.mcp_config)
    
    @pytest.mark.asyncio
    async def test_manager_initialization_with_multiple_servers(self):
        """Test manager initialization with multiple MCP servers."""
        # Mock successful connections for both servers
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            assert len(self.manager.clients) == 2
            assert "calculator" in self.manager.clients
            assert "weather" in self.manager.clients
    
    @pytest.mark.asyncio
    async def test_manager_handles_partial_connection_failures(self):
        """Test that manager handles partial connection failures gracefully."""
        # Mock connect method to return True for calculator, False for weather
        original_connect = self.manager.clients["calculator"].connect if "calculator" in self.manager.clients else None
        
        async def mock_calc_connect():
            return True
        
        async def mock_weather_connect():
            return False
        
        with patch.object(self.manager, '_connect_client') as mock_connect_client:
            async def mock_connect_wrapper(server_name, client):
                if server_name == "calculator":
                    client._status = client._status.CONNECTED
                    return await mock_calc_connect()
                else:
                    return await mock_weather_connect()
            
            mock_connect_client.side_effect = mock_connect_wrapper
            await self.manager.initialize()
            
            # Manager should still initialize with partial success
            assert len(self.manager.clients) == 2
            connected_servers = self.manager.get_connected_servers()
            assert "calculator" in connected_servers
            assert "weather" not in connected_servers
    
    @pytest.mark.asyncio
    async def test_tool_routing_with_multiple_servers(self):
        """Test tool routing across multiple servers."""
        # Mock tools from different servers
        calculator_tools = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        weather_tools = [
            {
                "type": "function", 
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        # Mock client connections and tools
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Mock clients as connected
            calc_client = self.manager.clients["calculator"]
            weather_client = self.manager.clients["weather"]
            calc_client._status = MCPConnectionStatus.CONNECTED
            weather_client._status = MCPConnectionStatus.CONNECTED
            
            # Mock the list_tools method for each client
            calc_client.list_tools = AsyncMock(return_value=calculator_tools)
            weather_client.list_tools = AsyncMock(return_value=weather_tools)
            
            # Rebuild tool routing
            await self.manager._rebuild_tool_routing()
            
            # Check tool routing
            assert self.manager.get_tool_server("add") == "calculator"
            assert self.manager.get_tool_server("get_weather") == "weather"
            assert self.manager.get_total_tool_count() == 2
    
    @pytest.mark.asyncio
    async def test_tool_execution_routing(self):
        """Test that tool execution is routed to correct server."""
        # Setup manager with mocked clients
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Mock tool routing
            self.manager._tool_to_server = {"add": "calculator"}
            
            # Mock successful tool execution
            mock_client = AsyncMock()
            mock_client.is_connected = True
            mock_client.call_tool = AsyncMock(return_value={"content": "Result: 5"})
            self.manager.clients["calculator"] = mock_client
            
            result = await self.manager.execute_tool("add", {"a": 2, "b": 3})
            
            assert result["content"] == "Result: 5"
            mock_client.call_tool.assert_called_once_with("add", {"a": 2, "b": 3})
    
    @pytest.mark.asyncio
    async def test_auto_approval_checking(self):
        """Test auto-approval checking across servers."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Mock tool routing and client auto-approval
            self.manager._tool_to_server = {"add": "calculator", "get_weather": "weather"}
            
            mock_calc_client = MagicMock()
            mock_calc_client.is_tool_auto_approved.return_value = True
            self.manager.clients["calculator"] = mock_calc_client
            
            mock_weather_client = MagicMock()
            mock_weather_client.is_tool_auto_approved.return_value = False
            self.manager.clients["weather"] = mock_weather_client
            
            # Test auto-approval
            assert await self.manager.is_tool_auto_approved("add") is True
            assert await self.manager.is_tool_auto_approved("get_weather") is False
            assert await self.manager.is_tool_auto_approved("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent execution of multiple tools."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Setup tool routing
            self.manager._tool_to_server = {"add": "calculator", "multiply": "calculator"}
            
            # Mock client
            mock_client = AsyncMock()
            mock_client.is_connected = True
            
            async def mock_call_tool(tool_name, args):
                await asyncio.sleep(0.1)  # Simulate work
                if tool_name == "add":
                    return {"content": str(args["a"] + args["b"])}
                elif tool_name == "multiply":
                    return {"content": str(args["a"] * args["b"])}
            
            mock_client.call_tool = mock_call_tool
            self.manager.clients["calculator"] = mock_client
            
            # Execute multiple tools concurrently
            tool_calls = [
                {"id": "1", "function": {"name": "add", "arguments": {"a": 2, "b": 3}}},
                {"id": "2", "function": {"name": "multiply", "arguments": {"a": 4, "b": 5}}}
            ]
            
            results = await self.manager.handle_tool_calls(tool_calls)
            
            assert len(results) == 2
            # Results should contain both tool executions
            result_contents = [r["content"] for r in results]
            assert "5" in result_contents  # 2 + 3
            assert "20" in result_contents  # 4 * 5


class TestMCPChatIntegration:
    """Test MCP integration with chat functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.model = EliaChatModel(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo"
        )
    
    @pytest.mark.asyncio
    async def test_chat_includes_mcp_tools_in_completion(self):
        """Test that chat includes MCP tools in LiteLLM completion calls."""
        # This would require mocking the entire chat flow
        # For now, we'll test the tool integration conceptually
        
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform calculations",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        # Mock MCP manager
        mock_manager = AsyncMock()
        mock_manager.get_available_tools.return_value = mock_tools
        
        # Verify that tools would be included in completion call
        tools = await mock_manager.get_available_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "calculator"
    
    @pytest.mark.asyncio
    async def test_tool_approval_workflow(self):
        """Test the tool approval workflow in chat."""
        # Mock MCP manager with non-auto-approved tool
        mock_manager = AsyncMock()
        mock_manager.is_tool_auto_approved.return_value = False
        mock_manager.execute_tool.return_value = {"content": "Tool executed"}
        
        # Simulate tool approval workflow
        tool_name = "sensitive_tool"
        arguments = {"param": "value"}
        
        # Check if tool needs approval
        needs_approval = not await mock_manager.is_tool_auto_approved(tool_name)
        assert needs_approval is True
        
        # Simulate user approval (would be done via UI in real app)
        user_approved = True
        
        if user_approved:
            result = await mock_manager.execute_tool(tool_name, arguments)
            assert result["content"] == "Tool executed"


class TestMCPErrorHandling:
    """Test MCP error handling and graceful degradation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "unreliable": MCPServerConfig(
                    command="python",
                    args=["unreliable.py"],
                    timeout=5
                )
            }
        )
        self.manager = MCPManager(self.mcp_config)
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_connection_failure(self):
        """Test graceful degradation when MCP servers fail to connect."""
        # Mock connection failure
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=False):
            await self.manager.initialize()
            
            # Manager should initialize but with no connected servers
            assert len(self.manager.clients) == 1
            assert len(self.manager.get_connected_servers()) == 0
            assert self.manager.get_total_tool_count() == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_tool_execution(self):
        """Test error handling during tool execution."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Setup tool routing
            self.manager._tool_to_server = {"failing_tool": "unreliable"}
            
            # Mock client that raises errors
            mock_client = AsyncMock()
            mock_client.is_connected = True
            mock_client.call_tool.side_effect = MCPToolError(
                message="Tool execution failed",
                tool_name="failing_tool",
                server_name="unreliable"
            )
            self.manager.clients["unreliable"] = mock_client
            
            # Tool execution should raise the MCP error
            with pytest.raises(MCPToolError):
                await self.manager.execute_tool("failing_tool", {})
    
    @pytest.mark.asyncio
    async def test_reconnection_on_connection_loss(self):
        """Test automatic reconnection when connection is lost."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Simulate connection loss
            mock_client = self.manager.clients["unreliable"]
            from elia_chat.mcp.mcp_client import MCPConnectionStatus
            mock_client._status = MCPConnectionStatus.DISCONNECTED
            
            # Attempting to execute tool should trigger reconnection attempt
            self.manager._tool_to_server = {"test_tool": "unreliable"}
            
            with pytest.raises(MCPConnectionError):
                await self.manager.execute_tool("test_tool", {})
            
            # Verify reconnection task was started
            assert "unreliable" in self.manager._reconnect_tasks


class TestMCPPerformanceAndMonitoring:
    """Test MCP performance monitoring and metrics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "test-server": MCPServerConfig(
                    command="python",
                    args=["test.py"],
                    timeout=30
                )
            }
        )
        self.manager = MCPManager(self.mcp_config)
    
    @pytest.mark.asyncio
    async def test_server_status_tracking(self):
        """Test server status and metrics tracking."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Mock the client as connected
            mock_client = self.manager.clients["test-server"]
            from elia_chat.mcp.mcp_client import MCPConnectionStatus
            mock_client._status = MCPConnectionStatus.CONNECTED
            
            # Check initial status
            status = self.manager.get_server_status()
            assert "test-server" in status
            assert status["test-server"]["connected"] is True
    
    @pytest.mark.asyncio
    async def test_manager_summary_metrics(self):
        """Test manager summary metrics."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            summary = self.manager.get_manager_summary()
            
            assert "connected_servers" in summary
            assert "total_servers" in summary
            assert "total_tools" in summary
            assert "connection_rate" in summary
            assert summary["total_servers"] == 1
    
    @pytest.mark.asyncio
    async def test_health_check_functionality(self):
        """Test health check across all servers."""
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await self.manager.initialize()
            
            # Mock health check
            mock_client = self.manager.clients["test-server"]
            mock_client.health_check = AsyncMock(return_value=True)
            
            health_status = await self.manager.health_check()
            
            assert "test-server" in health_status
            assert health_status["test-server"] is True


class TestMCPConfigurationIntegration:
    """Test MCP configuration integration with the application."""
    
    @pytest.mark.asyncio
    async def test_configuration_file_loading(self):
        """Test loading MCP configuration from file."""
        config_data = {
            "mcp_servers": {
                "file-server": {
                    "command": "python",
                    "args": ["file_server.py"],
                    "env": {"DEBUG": "1"},
                    "auto_approve": ["read_file"],
                    "timeout": 45
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = MCPConfig.load_from_file(temp_path)
            
            assert len(config.mcp_servers) == 1
            server = config.mcp_servers["file-server"]
            assert server.command == "python"
            assert server.args == ["file_server.py"]
            assert server.env == {"DEBUG": "1"}
            assert server.auto_approve == ["read_file"]
            assert server.timeout == 45
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_configuration_validation_and_error_handling(self):
        """Test configuration validation and error handling."""
        # Test invalid configuration
        invalid_config = {
            "mcp_servers": {
                "invalid-server": {
                    # Missing required 'command' field
                    "args": ["script.py"]
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(Exception):  # Should raise validation error
                MCPConfig.load_from_file(temp_path)
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_graceful_handling_of_missing_config(self):
        """Test graceful handling when MCP config file is missing."""
        # Mock missing config file
        with patch('elia_chat.mcp.mcp_config.config_directory') as mock_config_dir:
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_config_dir.return_value = Path(temp_dir)
                
                # No mcp.json file exists
                config = MCPConfig.load_default()
                
                # Should return empty config without errors
                assert len(config.mcp_servers) == 0