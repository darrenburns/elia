"""Unit tests for MCP client functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from elia_chat.mcp.mcp_client import (
    MCPClient, 
    MCPConnectionStatus
)
from elia_chat.mcp.exceptions import (
    MCPError,
    MCPConnectionError, 
    MCPToolError,
    MCPTimeoutError
)
from elia_chat.mcp.mcp_config import MCPServerConfig


class TestMCPClient:
    """Test MCPClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_config = MCPServerConfig(
            command="python",
            args=["test_server.py"],
            env={"DEBUG": "1"},
            timeout=30,
            auto_approve=["safe_tool"]
        )
        self.client = MCPClient("test-server", self.server_config)
    
    def test_init(self):
        """Test MCPClient initialization."""
        assert self.client.server_name == "test-server"
        assert self.client.config == self.server_config
        assert self.client.status == MCPConnectionStatus.DISCONNECTED
        assert not self.client.is_connected
        assert self.client.connection_error is None
    
    def test_status_properties(self):
        """Test status-related properties."""
        # Initially disconnected
        assert self.client.status == MCPConnectionStatus.DISCONNECTED
        assert not self.client.is_connected
        
        # Simulate connected state
        self.client._status = MCPConnectionStatus.CONNECTED
        assert self.client.status == MCPConnectionStatus.CONNECTED
        assert self.client.is_connected
        
        # Simulate error state
        self.client._status = MCPConnectionStatus.ERROR
        self.client._connection_error = "Test error"
        assert self.client.status == MCPConnectionStatus.ERROR
        assert not self.client.is_connected
        assert self.client.connection_error == "Test error"


class TestMCPClientConnection:
    """Test MCP client connection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_config = MCPServerConfig(command="python", args=["test.py"])
        self.client = MCPClient("test-server", self.server_config)
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """Test connecting when already connected."""
        self.client._status = MCPConnectionStatus.CONNECTED
        
        result = await self.client.connect()
        
        assert result is True
        assert self.client.status == MCPConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    @patch('elia_chat.mcp.mcp_client.stdio_client')
    async def test_connect_success(self, mock_stdio_client):
        """Test successful connection."""
        # Mock the stdio client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_session = AsyncMock()
        
        # Mock session methods
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
        
        # Mock the context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_stdio_client.return_value = mock_context
        
        # Mock ClientSession
        with patch('elia_chat.mcp.mcp_client.ClientSession', return_value=mock_session):
            result = await self.client.connect()
        
        assert result is True
        assert self.client.status == MCPConnectionStatus.CONNECTED
        assert self.client.connection_error is None
        mock_session.initialize.assert_called_once()
        mock_session.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('elia_chat.mcp.mcp_client.stdio_client')
    async def test_connect_failure(self, mock_stdio_client):
        """Test connection failure."""
        # Mock stdio_client to raise an exception
        mock_stdio_client.side_effect = Exception("Connection failed")
        
        result = await self.client.connect()
        
        assert result is False
        assert self.client.status == MCPConnectionStatus.ERROR
        assert self.client.connection_error is not None
    
    @pytest.mark.asyncio
    async def test_disconnect_no_session(self):
        """Test disconnecting when no session exists."""
        await self.client.disconnect()
        
        assert self.client.status == MCPConnectionStatus.DISCONNECTED
        assert self.client._session is None
    
    @pytest.mark.asyncio
    async def test_disconnect_with_session(self):
        """Test disconnecting with active session."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        self.client._session = mock_session
        self.client._status = MCPConnectionStatus.CONNECTED
        
        await self.client.disconnect()
        
        assert self.client.status == MCPConnectionStatus.DISCONNECTED
        assert self.client._session is None
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_session_close_error(self):
        """Test disconnecting when session close raises error."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock(side_effect=Exception("Close error"))
        self.client._session = mock_session
        self.client._status = MCPConnectionStatus.CONNECTED
        
        # Should not raise exception
        await self.client.disconnect()
        
        assert self.client.status == MCPConnectionStatus.DISCONNECTED
        assert self.client._session is None


class TestMCPClientTools:
    """Test MCP client tool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_config = MCPServerConfig(
            command="python", 
            args=["test.py"],
            auto_approve=["safe_tool"]
        )
        self.client = MCPClient("test-server", self.server_config)
        
        # Mock tools
        self.mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "safe_tool",
                    "description": "A safe tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        self.client._tools = self.mock_tools
        self.client._status = MCPConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self):
        """Test listing tools when not connected."""
        self.client._status = MCPConnectionStatus.DISCONNECTED
        
        with pytest.raises(MCPConnectionError):
            await self.client.list_tools()
    
    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """Test successful tool listing."""
        tools = await self.client.list_tools()
        
        assert len(tools) == 2
        assert tools[0]["function"]["name"] == "calculator"
        assert tools[1]["function"]["name"] == "safe_tool"
        # Ensure it returns a copy, not the original
        assert tools is not self.client._tools
    
    def test_get_tool_by_name_exists(self):
        """Test getting existing tool by name."""
        tool = self.client.get_tool_by_name("calculator")
        
        assert tool is not None
        assert tool["function"]["name"] == "calculator"
        assert tool["function"]["description"] == "Perform calculations"
    
    def test_get_tool_by_name_not_exists(self):
        """Test getting non-existent tool by name."""
        tool = self.client.get_tool_by_name("nonexistent")
        
        assert tool is None
    
    def test_is_tool_auto_approved_true(self):
        """Test checking auto-approved tool."""
        result = self.client.is_tool_auto_approved("safe_tool")
        
        assert result is True
    
    def test_is_tool_auto_approved_false(self):
        """Test checking non-auto-approved tool."""
        result = self.client.is_tool_auto_approved("calculator")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """Test calling tool when not connected."""
        self.client._status = MCPConnectionStatus.DISCONNECTED
        
        with pytest.raises(MCPConnectionError):
            await self.client.call_tool("calculator", {"expression": "2+2"})
    
    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        """Test calling non-existent tool."""
        # Need a mock session for connection check
        self.client._session = AsyncMock()
        
        with pytest.raises(MCPToolError, match="Tool 'nonexistent' not found"):
            await self.client.call_tool("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool call."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = [MagicMock(text="Result: 4")]
        
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        self.client._session = mock_session
        
        result = await self.client.call_tool("calculator", {"expression": "2+2"})
        
        assert result["success"] is True
        assert result["content"] == "Result: 4"
        assert result["tool_name"] == "calculator"
        assert result["server_name"] == "test-server"
        mock_session.call_tool.assert_called_once_with("calculator", {"expression": "2+2"})
    
    @pytest.mark.asyncio
    async def test_call_tool_error_result(self):
        """Test tool call with error result."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.isError = True
        mock_result.content = "Tool execution failed"
        
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        self.client._session = mock_session
        
        with pytest.raises(MCPToolError):
            await self.client.call_tool("calculator", {"expression": "invalid"})
    
    @pytest.mark.asyncio
    async def test_call_tool_timeout(self):
        """Test tool call timeout."""
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=asyncio.TimeoutError())
        self.client._session = mock_session
        
        with pytest.raises(MCPTimeoutError):
            await self.client.call_tool("calculator", {"expression": "2+2"})
    
    @pytest.mark.asyncio
    async def test_call_tool_exception(self):
        """Test tool call with exception."""
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("Network error"))
        self.client._session = mock_session
        
        with pytest.raises(MCPError):
            await self.client.call_tool("calculator", {"expression": "2+2"})
    
    @pytest.mark.asyncio
    async def test_refresh_tools_success(self):
        """Test successful tool refresh."""
        mock_session = AsyncMock()
        
        # Mock MCP tool format
        mock_mcp_tool = MagicMock()
        mock_mcp_tool.name = "test_tool"
        mock_mcp_tool.description = "Test tool description"
        mock_mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"]
        }
        
        mock_result = MagicMock()
        mock_result.tools = [mock_mcp_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        
        self.client._session = mock_session
        
        await self.client._refresh_tools()
        
        assert len(self.client._tools) == 1
        tool = self.client._tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "test_tool"
        assert tool["function"]["description"] == "Test tool description"
        assert tool["function"]["parameters"]["required"] == ["param"]
    
    @pytest.mark.asyncio
    async def test_refresh_tools_no_session(self):
        """Test tool refresh without session."""
        self.client._session = None
        
        with pytest.raises(MCPConnectionError):
            await self.client._refresh_tools()
    
    @pytest.mark.asyncio
    async def test_refresh_tools_exception(self):
        """Test tool refresh with exception."""
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(side_effect=Exception("List tools failed"))
        self.client._session = mock_session
        
        with pytest.raises(MCPError):
            await self.client._refresh_tools()


class TestMCPClientHealthCheck:
    """Test MCP client health check functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_config = MCPServerConfig(command="python", args=["test.py"])
        self.client = MCPClient("test-server", self.server_config)
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        result = await self.client.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
        
        self.client._session = mock_session
        self.client._status = MCPConnectionStatus.CONNECTED
        
        result = await self.client.health_check()
        
        assert result is True
        mock_session.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(side_effect=Exception("Health check failed"))
        
        self.client._session = mock_session
        self.client._status = MCPConnectionStatus.CONNECTED
        
        result = await self.client.health_check()
        
        assert result is False
        assert self.client.status == MCPConnectionStatus.ERROR
        assert "Health check failed" in self.client.connection_error


class TestMCPClientRepr:
    """Test MCPClient string representation."""
    
    def test_repr(self):
        """Test string representation of MCPClient."""
        server_config = MCPServerConfig(command="python", args=["test.py"])
        client = MCPClient("test-server", server_config)
        
        # Add some mock tools
        client._tools = [{"function": {"name": "tool1"}}, {"function": {"name": "tool2"}}]
        
        repr_str = repr(client)
        
        assert "MCPClient" in repr_str
        assert "test-server" in repr_str
        assert "disconnected" in repr_str
        assert "tools=2" in repr_str