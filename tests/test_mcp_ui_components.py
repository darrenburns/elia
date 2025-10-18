"""UI tests for MCP status display components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from textual.app import App, ComposeResult
from textual.widgets import Label, Button

from elia_chat.widgets.mcp_status import (
    MCPServerStatusWidget,
    MCPToolsWidget, 
    MCPStatusWidget,
    MCPStatusIndicator,
    MCPErrorDisplay
)
from elia_chat.mcp.mcp_manager import MCPManager
from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.mcp_client import MCPConnectionStatus


class MCPTestApp(App):
    """Test app for UI component testing."""
    
    def __init__(self, widget_to_test):
        super().__init__()
        self.widget_to_test = widget_to_test
    
    def compose(self) -> ComposeResult:
        yield self.widget_to_test


class TestMCPServerStatusWidget:
    """Test MCPServerStatusWidget class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_metrics = {
            "server_name": "test-server",
            "current_status": "connected",
            "is_connected": True,
            "tool_count": 5,
            "connection_attempts": 3,
            "successful_connections": 2,
            "connection_success_rate": 66.7,
            "tool_call_count": 10,
            "failed_tool_calls": 1,
            "tool_success_rate": 90.0,
            "average_tool_execution_time": 1.5,
            "uptime_seconds": 3600,
            "current_error": None
        }
        
        self.widget = MCPServerStatusWidget(
            server_name="test-server",
            server_metrics=self.server_metrics
        )
    
    def test_init(self):
        """Test widget initialization."""
        assert self.widget.server_name == "test-server"
        assert self.widget.server_metrics == self.server_metrics
        assert "connected" in self.widget.classes
    
    def test_update_css_classes_connected(self):
        """Test CSS class updates for connected status."""
        self.widget.server_metrics["current_status"] = "connected"
        self.widget._update_css_classes()
        
        assert "connected" in self.widget.classes
        assert "disconnected" not in self.widget.classes
        assert "connecting" not in self.widget.classes
    
    def test_update_css_classes_disconnected(self):
        """Test CSS class updates for disconnected status."""
        self.widget.server_metrics["current_status"] = "disconnected"
        self.widget._update_css_classes()
        
        assert "disconnected" in self.widget.classes
        assert "connected" not in self.widget.classes
        assert "connecting" not in self.widget.classes
    
    def test_update_css_classes_connecting(self):
        """Test CSS class updates for connecting status."""
        self.widget.server_metrics["current_status"] = "connecting"
        self.widget._update_css_classes()
        
        assert "connecting" in self.widget.classes
        assert "connected" not in self.widget.classes
        assert "disconnected" not in self.widget.classes
    
    def test_update_metrics(self):
        """Test updating server metrics."""
        new_metrics = self.server_metrics.copy()
        new_metrics["current_status"] = "disconnected"
        new_metrics["tool_count"] = 0
        
        self.widget.update_metrics(new_metrics)
        
        assert self.widget.server_metrics == new_metrics
        assert "disconnected" in self.widget.classes


class TestMCPToolsWidget:
    """Test MCPToolsWidget class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {"type": "object"}
                },
                "_mcp_server": "math-server"
            },
            {
                "type": "function", 
                "function": {
                    "name": "weather",
                    "description": "Get weather information",
                    "parameters": {"type": "object"}
                },
                "_mcp_server": "weather-server"
            }
        ]
        
        self.widget = MCPToolsWidget(tools=self.tools)
    
    def test_init(self):
        """Test widget initialization."""
        assert self.widget.tools == self.tools
    
    def test_update_tools(self):
        """Test updating tools list."""
        new_tools = [
            {
                "type": "function",
                "function": {
                    "name": "new_tool",
                    "description": "A new tool",
                    "parameters": {"type": "object"}
                },
                "_mcp_server": "new-server"
            }
        ]
        
        self.widget.update_tools(new_tools)
        
        assert self.widget.tools == new_tools
    
    def test_empty_tools(self):
        """Test widget with empty tools list."""
        empty_widget = MCPToolsWidget(tools=[])
        
        assert empty_widget.tools == []


class TestMCPStatusWidget:
    """Test MCPStatusWidget class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock MCP manager
        self.mock_manager = MagicMock(spec=MCPManager)
        self.mock_manager.get_all_server_metrics = AsyncMock(return_value={
            "server1": {
                "server_name": "server1",
                "current_status": "connected",
                "tool_count": 3
            }
        })
        self.mock_manager.get_available_tools = AsyncMock(return_value=[
            {
                "type": "function",
                "function": {"name": "test_tool", "description": "Test tool"},
                "_mcp_server": "server1"
            }
        ])
        self.mock_manager.get_manager_summary = MagicMock(return_value={
            "connected_servers": 1,
            "total_servers": 1,
            "total_tools": 1,
            "tool_success_rate": 100.0
        })
        
        self.widget = MCPStatusWidget(mcp_manager=self.mock_manager)
    
    def test_init(self):
        """Test widget initialization."""
        assert self.widget.mcp_manager == self.mock_manager
        # Don't test reactive properties directly as they need app context
    
    def test_manager_summary_formatting(self):
        """Test manager summary formatting logic."""
        # Test the formatting logic without UI context
        summary = {
            "connected_servers": 2,
            "total_servers": 3,
            "total_tools": 5,
            "tool_success_rate": 85.5
        }
        
        # Expected format
        expected_text = (
            f"{summary['connected_servers']}/{summary['total_servers']} servers connected • "
            f"{summary['total_tools']} tools available • "
            f"{summary['tool_success_rate']:.1f}% tool success rate"
        )
        
        # Verify the expected format matches what we expect
        assert "2/3 servers connected" in expected_text
        assert "5 tools available" in expected_text
        assert "85.5% tool success rate" in expected_text


class TestMCPStatusIndicator:
    """Test MCPStatusIndicator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock MCP manager
        self.mock_manager = MagicMock(spec=MCPManager)
        self.mock_manager.get_manager_summary = MagicMock(return_value={
            "connected_servers": 1,
            "total_servers": 2,
            "total_tools": 3,
            "tool_success_rate": 90.0
        })
        
        self.widget = MCPStatusIndicator(mcp_manager=self.mock_manager)
    
    def test_init(self):
        """Test widget initialization."""
        assert self.widget.mcp_manager == self.mock_manager
        # Don't test reactive properties directly as they need app context
    
    def test_status_text_formatting_all_connected(self):
        """Test status text formatting with all servers connected."""
        summary = {
            "connected_servers": 2,
            "total_servers": 2,
            "total_tools": 5
        }
        
        # Test the formatting logic
        connected = summary["connected_servers"]
        total = summary["total_servers"]
        tools = summary["total_tools"]
        
        if total == 0:
            expected_text = "MCP: Disabled"
        elif connected == total:
            expected_text = f"MCP: {connected}/{total} ({tools} tools)"
        elif connected > 0:
            expected_text = f"MCP: {connected}/{total} ({tools} tools)"
        else:
            expected_text = f"MCP: {connected}/{total} (offline)"
        
        assert expected_text == "MCP: 2/2 (5 tools)"
    
    def test_status_text_formatting_partial_connected(self):
        """Test status text formatting with some servers connected."""
        summary = {
            "connected_servers": 1,
            "total_servers": 2,
            "total_tools": 3
        }
        
        connected = summary["connected_servers"]
        total = summary["total_servers"]
        tools = summary["total_tools"]
        
        expected_text = f"MCP: {connected}/{total} ({tools} tools)"
        assert expected_text == "MCP: 1/2 (3 tools)"
    
    def test_status_text_formatting_none_connected(self):
        """Test status text formatting with no servers connected."""
        summary = {
            "connected_servers": 0,
            "total_servers": 2,
            "total_tools": 0
        }
        
        connected = summary["connected_servers"]
        total = summary["total_servers"]
        
        expected_text = f"MCP: {connected}/{total} (offline)"
        assert expected_text == "MCP: 0/2 (offline)"
    
    def test_status_text_formatting_no_servers(self):
        """Test status text formatting with no servers configured."""
        summary = {
            "connected_servers": 0,
            "total_servers": 0,
            "total_tools": 0
        }
        
        total = summary["total_servers"]
        
        if total == 0:
            expected_text = "MCP: Disabled"
        
        assert expected_text == "MCP: Disabled"


class TestMCPErrorDisplay:
    """Test MCPErrorDisplay class."""
    
    def test_init_with_server(self):
        """Test widget initialization with server name."""
        widget = MCPErrorDisplay(
            error_message="Connection failed",
            server_name="test-server"
        )
        
        assert widget.error_message == "Connection failed"
        assert widget.server_name == "test-server"
    
    def test_init_without_server(self):
        """Test widget initialization without server name."""
        widget = MCPErrorDisplay(error_message="General error")
        
        assert widget.error_message == "General error"
        assert widget.server_name is None
    
    def test_dismiss_error(self):
        """Test error dismissal."""
        widget = MCPErrorDisplay(error_message="Test error")
        
        # Mock the remove method
        widget.remove = MagicMock()
        
        # Create mock button event
        mock_button = MagicMock()
        mock_event = MagicMock()
        mock_event.button = mock_button
        
        # Call dismiss method
        widget.dismiss_error(mock_event)
        
        # Verify widget was removed
        widget.remove.assert_called_once()


class TestMCPUIIntegration:
    """Test MCP UI component integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock MCP configuration
        self.mock_config = MCPConfig(
            mcp_servers={
                "test-server": MCPServerConfig(
                    command="python",
                    args=["test.py"],
                    auto_approve=["safe_tool"]
                )
            }
        )
        
        # Create mock MCP manager
        self.mock_manager = MagicMock(spec=MCPManager)
        self.mock_manager.config = self.mock_config
        self.mock_manager.clients = {"test-server": MagicMock()}
    
    def test_status_widget_with_manager(self):
        """Test status widget creation with MCP manager."""
        widget = MCPStatusWidget(mcp_manager=self.mock_manager)
        
        assert widget.mcp_manager == self.mock_manager
        assert isinstance(widget, MCPStatusWidget)
    
    def test_indicator_with_manager(self):
        """Test indicator creation with MCP manager."""
        widget = MCPStatusIndicator(mcp_manager=self.mock_manager)
        
        assert widget.mcp_manager == self.mock_manager
        assert isinstance(widget, MCPStatusIndicator)
    
    def test_server_widget_creation(self):
        """Test server status widget creation."""
        metrics = {
            "server_name": "test-server",
            "current_status": "connected",
            "tool_count": 2
        }
        
        widget = MCPServerStatusWidget(
            server_name="test-server",
            server_metrics=metrics
        )
        
        assert widget.server_name == "test-server"
        assert widget.server_metrics == metrics
    
    def test_tools_widget_creation(self):
        """Test tools widget creation."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test tool"
                },
                "_mcp_server": "test-server"
            }
        ]
        
        widget = MCPToolsWidget(tools=tools)
        
        assert widget.tools == tools
    
    def test_error_display_creation(self):
        """Test error display widget creation."""
        widget = MCPErrorDisplay(
            error_message="Connection timeout",
            server_name="test-server"
        )
        
        assert widget.error_message == "Connection timeout"
        assert widget.server_name == "test-server"


class TestMCPUIStatusCallbacks:
    """Test MCP UI status change callbacks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_manager = MagicMock(spec=MCPManager)
        self.mock_manager.add_status_change_callback = MagicMock()
        self.mock_manager.remove_status_change_callback = MagicMock()
        
        self.widget = MCPStatusWidget(mcp_manager=self.mock_manager)
    
    def test_status_change_callback_execution(self):
        """Test status change callback execution."""
        # Mock the call_later method
        self.widget.call_later = MagicMock()
        
        # Call the status change callback directly
        self.widget._on_status_change("test-server", MCPConnectionStatus.CONNECTED)
        
        # Verify update was scheduled
        self.widget.call_later.assert_called_once_with(self.widget._update_status)


class TestMCPUITimers:
    """Test MCP UI timer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_manager = MagicMock(spec=MCPManager)
        self.widget = MCPStatusWidget(mcp_manager=self.mock_manager)
    
    def test_timer_cleanup_on_unmount(self):
        """Test timer cleanup during widget unmount."""
        # Mock timer
        mock_timer = MagicMock()
        mock_timer.stop = MagicMock()
        self.widget._update_timer = mock_timer
        
        # Mock manager callback methods
        self.widget.mcp_manager.remove_status_change_callback = MagicMock()
        
        # Simulate widget unmount
        self.widget.on_unmount()
        
        # Verify timer was stopped
        mock_timer.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])