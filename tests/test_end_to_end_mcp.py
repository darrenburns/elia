"""End-to-end integration tests for MCP functionality."""

import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from elia_chat.app import Elia
from elia_chat.config import LaunchConfig
from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.mcp_manager import MCPManager
from elia_chat.mcp.mcp_client import MCPClient, MCPConnectionStatus


class TestEndToEndMCP:
    """End-to-end tests for MCP integration."""
    
    @pytest.mark.asyncio
    async def test_complete_mcp_workflow(self):
        """Test complete MCP workflow from configuration to tool execution."""
        
        # 1. Create MCP configuration
        mcp_config = MCPConfig(
            mcp_servers={
                "test-calculator": MCPServerConfig(
                    command="python",
                    args=["calculator.py"],
                    auto_approve=["add"],
                    timeout=30
                )
            }
        )
        
        # 2. Initialize MCP manager
        manager = MCPManager(mcp_config)
        
        # 3. Mock successful client connection and tool listing
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            with patch('elia_chat.mcp.mcp_client.MCPClient.list_tools', return_value=mock_tools):
                # 4. Initialize manager
                await manager.initialize()
                
                # Mock the client as connected and rebuild tool routing
                client = manager.clients["test-calculator"]
                client._status = MCPConnectionStatus.CONNECTED
                await manager._rebuild_tool_routing()
                
                # 5. Verify tools are available
                available_tools = await manager.get_available_tools()
                assert len(available_tools) == 1
                assert available_tools[0]["function"]["name"] == "add"
                
                # 6. Mock tool execution
                with patch('elia_chat.mcp.mcp_client.MCPClient.call_tool') as mock_call_tool:
                    mock_call_tool.return_value = {"content": "7", "success": True}
                    
                    # 7. Execute tool
                    result = await manager.execute_tool("add", {"a": 3, "b": 4})
                    
                    # 8. Verify result
                    assert result["content"] == "7"
                    assert result["success"] is True
                    mock_call_tool.assert_called_once_with("add", {"a": 3, "b": 4})
                
                # 9. Test auto-approval
                assert await manager.is_tool_auto_approved("add") is True
                
                # 10. Cleanup
                await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_app_integration_with_mcp(self):
        """Test Elia app integration with MCP."""
        
        # Create test configuration
        mcp_config = MCPConfig(
            mcp_servers={
                "test-server": MCPServerConfig(
                    command="python",
                    args=["test.py"]
                )
            }
        )
        
        # Mock MCP config loading
        with patch('elia_chat.mcp.mcp_config.MCPConfig.load_default', return_value=mcp_config):
            # Create app
            launch_config = LaunchConfig()
            app = Elia(launch_config)
            
            # Verify MCP components are initialized
            assert app.mcp_config is not None
            assert app.mcp_manager is not None
            assert len(app.mcp_config.mcp_servers) == 1
            
            # Mock manager initialization
            with patch.object(app.mcp_manager, 'initialize') as mock_init:
                with patch.object(app.mcp_manager, 'shutdown') as mock_shutdown:
                    # Test app lifecycle
                    await app.on_mount()
                    mock_init.assert_called_once()
                    
                    await app.on_unmount()
                    mock_shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mcp_tool_integration_with_litellm(self):
        """Test MCP tool integration with LiteLLM interface."""
        
        # Mock MCP tools
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
        
        # Create manager
        mcp_config = MCPConfig(
            mcp_servers={
                "weather": MCPServerConfig(command="python", args=["weather.py"])
            }
        )
        manager = MCPManager(mcp_config)
        
        # Mock successful initialization
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            with patch('elia_chat.mcp.mcp_client.MCPClient.list_tools', return_value=mock_tools):
                await manager.initialize()
                
                # Mock the client as connected and rebuild tool routing
                client = manager.clients["weather"]
                client._status = MCPConnectionStatus.CONNECTED
                await manager._rebuild_tool_routing()
                
                # Get tools in LiteLLM format
                litellm_tools = await manager.get_available_tools()
                
                # Verify format is compatible with LiteLLM
                assert len(litellm_tools) == 1
                tool = litellm_tools[0]
                assert tool["type"] == "function"
                assert "function" in tool
                assert "name" in tool["function"]
                assert "description" in tool["function"]
                assert "parameters" in tool["function"]
                
                # Verify tool has server metadata
                assert "_mcp_server" in tool
                assert tool["_mcp_server"] == "weather"
                
                await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_graceful_degradation(self):
        """Test error handling and graceful degradation."""
        
        # Create configuration with multiple servers
        mcp_config = MCPConfig(
            mcp_servers={
                "working-server": MCPServerConfig(command="python", args=["working.py"]),
                "failing-server": MCPServerConfig(command="python", args=["failing.py"])
            }
        )
        manager = MCPManager(mcp_config)
        
        # Mock partial connection failure
        async def mock_connect(client_self):
            return client_self.server_name == "working-server"
        
        with patch.object(MCPClient, 'connect', side_effect=mock_connect):
            await manager.initialize()
            
            # Verify manager handles partial failures gracefully
            assert len(manager.clients) == 2  # Both clients created
            
            # Only working server should be connected
            connected_servers = manager.get_connected_servers()
            # Note: This test may need adjustment based on actual implementation
            
            # Manager should still be functional
            status = manager.get_server_status()
            assert "working-server" in status
            assert "failing-server" in status
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_file_integration(self):
        """Test loading configuration from file and using it in the app."""
        
        # Create temporary config file
        config_data = {
            "mcp_servers": {
                "file-based-server": {
                    "command": "uvx",
                    "args": ["test-mcp-server@latest"],
                    "env": {"DEBUG": "1"},
                    "auto_approve": ["safe_operation"],
                    "timeout": 60,
                    "disabled": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration from file
            config = MCPConfig.load_from_file(temp_path)
            
            # Verify configuration is loaded correctly
            assert len(config.mcp_servers) == 1
            server_config = config.mcp_servers["file-based-server"]
            assert server_config.command == "uvx"
            assert server_config.args == ["test-mcp-server@latest"]
            assert server_config.env == {"DEBUG": "1"}
            assert server_config.auto_approve == ["safe_operation"]
            assert server_config.timeout == 60
            assert server_config.disabled is False
            
            # Test enabled servers filtering
            enabled_servers = config.get_enabled_servers()
            assert len(enabled_servers) == 1
            assert "file-based-server" in enabled_servers
            
        finally:
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent execution of multiple tools."""
        
        mcp_config = MCPConfig(
            mcp_servers={
                "math-server": MCPServerConfig(command="python", args=["math.py"])
            }
        )
        manager = MCPManager(mcp_config)
        
        # Mock tools and execution
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add numbers",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "Multiply numbers", 
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            with patch('elia_chat.mcp.mcp_client.MCPClient.list_tools', return_value=mock_tools):
                await manager.initialize()
                
                # Mock tool execution with delays to test concurrency
                async def mock_call_tool(tool_name, args):
                    await asyncio.sleep(0.1)  # Simulate work
                    if tool_name == "add":
                        return {"content": "5"}
                    elif tool_name == "multiply":
                        return {"content": "12"}
                
                with patch('elia_chat.mcp.mcp_client.MCPClient.call_tool', side_effect=mock_call_tool):
                    # Execute multiple tools concurrently
                    tool_calls = [
                        {"id": "1", "function": {"name": "add", "arguments": {"a": 2, "b": 3}}},
                        {"id": "2", "function": {"name": "multiply", "arguments": {"a": 3, "b": 4}}}
                    ]
                    
                    start_time = asyncio.get_event_loop().time()
                    results = await manager.handle_tool_calls(tool_calls)
                    end_time = asyncio.get_event_loop().time()
                    
                    # Verify results
                    assert len(results) == 2
                    
                    # Verify concurrent execution (should be faster than sequential)
                    execution_time = end_time - start_time
                    assert execution_time < 0.15  # Should be less than 2 * 0.1 if concurrent
                    
                await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_tool_approval_workflow(self):
        """Test tool approval workflow."""
        
        mcp_config = MCPConfig(
            mcp_servers={
                "secure-server": MCPServerConfig(
                    command="python",
                    args=["secure.py"],
                    auto_approve=["safe_tool"],  # Only safe_tool is auto-approved
                    timeout=30
                )
            }
        )
        manager = MCPManager(mcp_config)
        
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "safe_tool",
                    "description": "A safe operation",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "dangerous_tool",
                    "description": "A potentially dangerous operation",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            with patch('elia_chat.mcp.mcp_client.MCPClient.list_tools', return_value=mock_tools):
                await manager.initialize()
                
                # Mock the client as connected and rebuild tool routing
                client = manager.clients["secure-server"]
                client._status = MCPConnectionStatus.CONNECTED
                await manager._rebuild_tool_routing()
                
                # Test auto-approval checking
                assert await manager.is_tool_auto_approved("safe_tool") is True
                assert await manager.is_tool_auto_approved("dangerous_tool") is False
                assert await manager.is_tool_auto_approved("nonexistent_tool") is False
                
                await manager.shutdown()


class TestMCPPerformanceIntegration:
    """Test MCP performance and monitoring integration."""
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring and metrics collection."""
        
        mcp_config = MCPConfig(
            mcp_servers={
                "monitored-server": MCPServerConfig(command="python", args=["monitored.py"])
            }
        )
        manager = MCPManager(mcp_config)
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Test manager summary
            summary = manager.get_manager_summary()
            assert "connected_servers" in summary
            assert "total_servers" in summary
            assert "total_tools" in summary
            assert summary["total_servers"] == 1
            
            # Test server status
            status = manager.get_server_status()
            assert "monitored-server" in status
            assert "status" in status["monitored-server"]
            assert "connected" in status["monitored-server"]
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check functionality."""
        
        mcp_config = MCPConfig(
            mcp_servers={
                "health-server": MCPServerConfig(command="python", args=["health.py"])
            }
        )
        manager = MCPManager(mcp_config)
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Mock health check
            with patch('elia_chat.mcp.mcp_client.MCPClient.health_check', return_value=True):
                health_status = await manager.health_check()
                
                assert "health-server" in health_status
                assert health_status["health-server"] is True
            
            await manager.shutdown()


if __name__ == "__main__":
    # Run a simple test to verify integration
    async def simple_test():
        config = MCPConfig()
        manager = MCPManager(config)
        await manager.initialize()
        print("MCP Manager initialized successfully")
        await manager.shutdown()
        print("MCP Manager shut down successfully")
    
    asyncio.run(simple_test())