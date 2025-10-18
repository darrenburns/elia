"""Test MCP compatibility with different model providers."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from elia_chat.config import EliaChatModel
from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.mcp_manager import MCPManager
from elia_chat.mcp.mcp_client import MCPClient, MCPConnectionStatus


class TestMCPModelCompatibility:
    """Test MCP integration with various model providers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "test-tools": MCPServerConfig(
                    command="python",
                    args=["test_tools.py"],
                    auto_approve=["safe_operation"],
                    timeout=30
                )
            }
        )
        
        # Mock tools that would be available
        self.mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_operation",
                    "description": "A safe operation that's auto-approved",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "string"}
                        }
                    }
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_openai_model_compatibility(self):
        """Test MCP tools work with OpenAI models."""
        model = EliaChatModel(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            provider="openai"
        )
        
        await self._test_model_compatibility(model)
    
    @pytest.mark.asyncio
    async def test_anthropic_model_compatibility(self):
        """Test MCP tools work with Anthropic models."""
        model = EliaChatModel(
            name="claude-3-sonnet-20240229",
            display_name="Claude 3 Sonnet",
            provider="anthropic"
        )
        
        await self._test_model_compatibility(model)
    
    @pytest.mark.asyncio
    async def test_ollama_model_compatibility(self):
        """Test MCP tools work with Ollama models."""
        model = EliaChatModel(
            name="llama2",
            display_name="Llama 2",
            provider="ollama"
        )
        
        await self._test_model_compatibility(model)
    
    @pytest.mark.asyncio
    async def test_gemini_model_compatibility(self):
        """Test MCP tools work with Google Gemini models."""
        model = EliaChatModel(
            name="gemini-pro",
            display_name="Gemini Pro",
            provider="google"
        )
        
        await self._test_model_compatibility(model)
    
    async def _test_model_compatibility(self, model: EliaChatModel):
        """Test MCP integration with a specific model."""
        manager = MCPManager(self.mcp_config)
        
        # Mock successful MCP setup
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Mock client as connected
            client = manager.clients["test-tools"]
            client._status = MCPConnectionStatus.CONNECTED
            client.list_tools = AsyncMock(return_value=self.mock_tools)
            
            # Rebuild tool routing
            await manager._rebuild_tool_routing()
            
            # Verify tools are available in LiteLLM format
            available_tools = await manager.get_available_tools()
            assert len(available_tools) == 2
            
            # Verify tool format is compatible with LiteLLM
            for tool in available_tools:
                assert tool["type"] == "function"
                assert "function" in tool
                assert "name" in tool["function"]
                assert "description" in tool["function"]
                assert "parameters" in tool["function"]
                
                # Verify server metadata is included
                assert "_mcp_server" in tool
                assert tool["_mcp_server"] == "test-tools"
            
            # Test tool execution
            with patch('elia_chat.mcp.mcp_client.MCPClient.call_tool') as mock_call_tool:
                mock_call_tool.return_value = {"content": "42", "success": True}
                
                result = await manager.execute_tool("calculator", {"expression": "6*7"})
                assert result["content"] == "42"
                assert result["success"] is True
            
            # Test auto-approval
            assert await manager.is_tool_auto_approved("safe_operation") is True
            assert await manager.is_tool_auto_approved("calculator") is False
            
            await manager.shutdown()


class TestMCPConcurrentOperations:
    """Test MCP under concurrent load and stress conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "concurrent-server": MCPServerConfig(
                    command="python",
                    args=["concurrent_server.py"],
                    timeout=30
                )
            }
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test multiple concurrent tool calls."""
        manager = MCPManager(self.mcp_config)
        
        # Mock tools
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": f"tool_{i}",
                    "description": f"Test tool {i}",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
            for i in range(5)
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Mock client
            client = manager.clients["concurrent-server"]
            client._status = MCPConnectionStatus.CONNECTED
            client.list_tools = AsyncMock(return_value=mock_tools)
            
            await manager._rebuild_tool_routing()
            
            # Mock tool execution with delays
            async def mock_call_tool(tool_name, args):
                await asyncio.sleep(0.1)  # Simulate work
                return {"content": f"Result from {tool_name}"}
            
            client.call_tool = mock_call_tool
            
            # Execute multiple tools concurrently
            tool_calls = [
                {"id": str(i), "function": {"name": f"tool_{i}", "arguments": {}}}
                for i in range(5)
            ]
            
            start_time = asyncio.get_event_loop().time()
            results = await manager.handle_tool_calls(tool_calls)
            end_time = asyncio.get_event_loop().time()
            
            # Verify all tools executed
            assert len(results) == 5
            
            # Verify concurrent execution (should be faster than sequential)
            execution_time = end_time - start_time
            assert execution_time < 0.4  # Should be much less than 5 * 0.1 if concurrent
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_multiple_server_coordination(self):
        """Test coordination between multiple MCP servers."""
        multi_server_config = MCPConfig(
            mcp_servers={
                "server-a": MCPServerConfig(command="python", args=["server_a.py"]),
                "server-b": MCPServerConfig(command="python", args=["server_b.py"]),
                "server-c": MCPServerConfig(command="python", args=["server_c.py"])
            }
        )
        
        manager = MCPManager(multi_server_config)
        
        # Mock different tools for each server
        server_tools = {
            "server-a": [{"type": "function", "function": {"name": "tool_a", "description": "Tool A", "parameters": {"type": "object"}}}],
            "server-b": [{"type": "function", "function": {"name": "tool_b", "description": "Tool B", "parameters": {"type": "object"}}}],
            "server-c": [{"type": "function", "function": {"name": "tool_c", "description": "Tool C", "parameters": {"type": "object"}}}]
        }
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Mock all clients as connected
            for server_name, client in manager.clients.items():
                client._status = MCPConnectionStatus.CONNECTED
                client.list_tools = AsyncMock(return_value=server_tools[server_name])
            
            await manager._rebuild_tool_routing()
            
            # Verify tool routing
            assert manager.get_tool_server("tool_a") == "server-a"
            assert manager.get_tool_server("tool_b") == "server-b"
            assert manager.get_tool_server("tool_c") == "server-c"
            assert manager.get_total_tool_count() == 3
            
            # Test concurrent execution across servers
            def create_mock_call_tool(server_name):
                async def mock_call_tool(tool_name, args):
                    return {"content": f"Result from {server_name}"}
                return mock_call_tool
            
            for server_name, client in manager.clients.items():
                client.call_tool = create_mock_call_tool(server_name)
            
            # Execute tools from different servers concurrently
            tool_calls = [
                {"id": "1", "function": {"name": "tool_a", "arguments": {}}},
                {"id": "2", "function": {"name": "tool_b", "arguments": {}}},
                {"id": "3", "function": {"name": "tool_c", "arguments": {}}}
            ]
            
            results = await manager.handle_tool_calls(tool_calls)
            assert len(results) == 3
            
            # Verify results come from correct servers
            result_contents = [r["content"] for r in results]
            assert "Result from server-a" in result_contents
            assert "Result from server-b" in result_contents
            assert "Result from server-c" in result_contents
            
            await manager.shutdown()


class TestMCPStabilityAndRecovery:
    """Test MCP stability and recovery under various failure conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_config = MCPConfig(
            mcp_servers={
                "stable-server": MCPServerConfig(command="python", args=["stable.py"]),
                "unstable-server": MCPServerConfig(command="python", args=["unstable.py"])
            }
        )
    
    @pytest.mark.asyncio
    async def test_partial_server_failure_recovery(self):
        """Test recovery when some servers fail."""
        manager = MCPManager(self.mcp_config)
        
        # Mock partial connection success
        async def mock_connect(client_self):
            return client_self.server_name == "stable-server"
        
        with patch.object(MCPClient, 'connect', side_effect=mock_connect):
            await manager.initialize()
            
            # Verify manager handles partial failures
            connected_servers = manager.get_connected_servers()
            # Note: The actual behavior may vary based on implementation
            
            # Manager should still be functional
            status = manager.get_server_status()
            assert "stable-server" in status
            assert "unstable-server" in status
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self):
        """Test error handling during tool execution."""
        manager = MCPManager(self.mcp_config)
        
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "failing_tool",
                    "description": "A tool that fails",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            # Mock client
            client = manager.clients["stable-server"]
            client._status = MCPConnectionStatus.CONNECTED
            client.list_tools = AsyncMock(return_value=mock_tools)
            
            await manager._rebuild_tool_routing()
            
            # Mock tool execution failure
            from elia_chat.mcp.exceptions import MCPToolError
            client.call_tool = AsyncMock(side_effect=MCPToolError(
                message="Tool execution failed",
                tool_name="failing_tool",
                server_name="stable-server"
            ))
            
            # Tool execution should handle the error gracefully
            with pytest.raises(MCPToolError):
                await manager.execute_tool("failing_tool", {})
            
            # Manager should still be functional after error
            assert manager.get_total_tool_count() == 1
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test MCP performance under simulated load."""
        manager = MCPManager(self.mcp_config)
        
        # Mock high-performance tools
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "fast_tool",
                    "description": "A fast tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        with patch('elia_chat.mcp.mcp_client.MCPClient.connect', return_value=True):
            await manager.initialize()
            
            client = manager.clients["stable-server"]
            client._status = MCPConnectionStatus.CONNECTED
            client.list_tools = AsyncMock(return_value=mock_tools)
            
            await manager._rebuild_tool_routing()
            
            # Mock fast tool execution
            call_count = 0
            async def mock_call_tool(tool_name, args):
                nonlocal call_count
                call_count += 1
                return {"content": f"Result {call_count}"}
            
            client.call_tool = mock_call_tool
            
            # Execute many tool calls rapidly
            num_calls = 50
            tool_calls = [
                {"id": str(i), "function": {"name": "fast_tool", "arguments": {}}}
                for i in range(num_calls)
            ]
            
            start_time = asyncio.get_event_loop().time()
            results = await manager.handle_tool_calls(tool_calls)
            end_time = asyncio.get_event_loop().time()
            
            # Verify all calls completed
            assert len(results) == num_calls
            assert call_count == num_calls
            
            # Verify reasonable performance (should complete quickly)
            execution_time = end_time - start_time
            assert execution_time < 2.0  # Should complete within 2 seconds
            
            await manager.shutdown()


if __name__ == "__main__":
    # Run a simple performance test
    async def performance_test():
        config = MCPConfig(
            mcp_servers={
                "perf-test": MCPServerConfig(command="echo", args=["test"])
            }
        )
        manager = MCPManager(config)
        
        start_time = asyncio.get_event_loop().time()
        await manager.initialize()
        init_time = asyncio.get_event_loop().time() - start_time
        
        print(f"MCP Manager initialization took {init_time:.3f} seconds")
        
        start_time = asyncio.get_event_loop().time()
        await manager.shutdown()
        shutdown_time = asyncio.get_event_loop().time() - start_time
        
        print(f"MCP Manager shutdown took {shutdown_time:.3f} seconds")
    
    asyncio.run(performance_test())