"""MCP status display widget for showing server connection status and available tools."""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime, timedelta

from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Console, ConsoleOptions, RenderResult
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.reactive import reactive, Reactive
from textual.widget import Widget
from textual.widgets import Static, Label, Button, Collapsible, DataTable
from textual.timer import Timer

from elia_chat.mcp.mcp_manager import MCPManager
from elia_chat.mcp.mcp_client import MCPConnectionStatus

if TYPE_CHECKING:
    from elia_chat.app import Elia


class MCPServerStatusWidget(Widget):
    """Widget displaying status for a single MCP server."""
    
    DEFAULT_CSS = """
    MCPServerStatusWidget {
        height: auto;
        margin: 1;
        padding: 1;
        border: solid $primary;
    }
    
    MCPServerStatusWidget.connected {
        border: solid $success;
    }
    
    MCPServerStatusWidget.disconnected {
        border: solid $error;
    }
    
    MCPServerStatusWidget.connecting {
        border: solid $warning;
    }
    
    .server-name {
        text-style: bold;
        color: $text;
    }
    
    .status-connected {
        color: $success;
        text-style: bold;
    }
    
    .status-disconnected {
        color: $error;
        text-style: bold;
    }
    
    .status-connecting {
        color: $warning;
        text-style: bold;
    }
    
    .metric-label {
        color: $text-muted;
    }
    
    .metric-value {
        color: $text;
        text-style: bold;
    }
    
    .error-text {
        color: $error;
        text-style: italic;
    }
    """
    
    def __init__(
        self,
        server_name: str,
        server_metrics: Dict[str, Any],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.server_name = server_name
        self.server_metrics = server_metrics
        self._update_css_classes()
    
    def _update_css_classes(self) -> None:
        """Update CSS classes based on connection status."""
        # Remove existing status classes
        self.remove_class("connected", "disconnected", "connecting")
        
        # Add appropriate status class
        status = self.server_metrics.get("current_status", "disconnected")
        if status == "connected":
            self.add_class("connected")
        elif status == "connecting":
            self.add_class("connecting")
        else:
            self.add_class("disconnected")
    
    def update_metrics(self, server_metrics: Dict[str, Any]) -> None:
        """Update server metrics and refresh display."""
        self.server_metrics = server_metrics
        self._update_css_classes()
        self.refresh()
    
    def compose(self) -> ComposeResult:
        """Compose the server status widget."""
        with Vertical():
            # Server name and status
            yield Label(
                f"{self.server_name}",
                classes="server-name",
                id=f"server-name-{self.server_name}"
            )
            
            # Connection status
            status = self.server_metrics.get("current_status", "disconnected")
            status_text = status.replace("_", " ").title()
            status_class = f"status-{status.replace('_', '-')}"
            
            yield Label(
                f"Status: {status_text}",
                classes=status_class,
                id=f"status-{self.server_name}"
            )
            
            # Tool count
            tool_count = self.server_metrics.get("tool_count", 0)
            yield Label(
                f"Tools: {tool_count}",
                classes="metric-value",
                id=f"tools-{self.server_name}"
            )
            
            # Connection metrics
            if self.server_metrics.get("connection_attempts", 0) > 0:
                success_rate = self.server_metrics.get("connection_success_rate", 0)
                yield Label(
                    f"Connection Rate: {success_rate:.1f}%",
                    classes="metric-value",
                    id=f"conn-rate-{self.server_name}"
                )
            
            # Tool execution metrics
            tool_calls = self.server_metrics.get("tool_call_count", 0)
            if tool_calls > 0:
                tool_success_rate = self.server_metrics.get("tool_success_rate", 0)
                avg_time = self.server_metrics.get("average_tool_execution_time", 0)
                
                yield Label(
                    f"Tool Calls: {tool_calls} ({tool_success_rate:.1f}% success)",
                    classes="metric-value",
                    id=f"tool-calls-{self.server_name}"
                )
                
                yield Label(
                    f"Avg Execution: {avg_time:.2f}s",
                    classes="metric-value",
                    id=f"avg-time-{self.server_name}"
                )
            
            # Uptime
            uptime_seconds = self.server_metrics.get("uptime_seconds")
            if uptime_seconds is not None and uptime_seconds > 0:
                uptime = timedelta(seconds=uptime_seconds)
                uptime_str = str(uptime).split('.')[0]  # Remove microseconds
                yield Label(
                    f"Uptime: {uptime_str}",
                    classes="metric-value",
                    id=f"uptime-{self.server_name}"
                )
            
            # Error information
            error = self.server_metrics.get("current_error")
            if error:
                yield Label(
                    f"Error: {error}",
                    classes="error-text",
                    id=f"error-{self.server_name}"
                )


class MCPToolsWidget(Widget):
    """Widget displaying available MCP tools."""
    
    DEFAULT_CSS = """
    MCPToolsWidget {
        height: auto;
        margin: 1;
        padding: 1;
        border: solid $primary;
    }
    
    .tools-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    
    .tool-item {
        margin-left: 2;
        margin-bottom: 1;
    }
    
    .tool-name {
        color: $accent;
        text-style: bold;
    }
    
    .tool-server {
        color: $text-muted;
        text-style: italic;
    }
    
    .tool-description {
        color: $text;
    }
    
    .no-tools {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    def __init__(
        self,
        tools: List[Dict[str, Any]],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.tools = tools
    
    def update_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Update tools list and refresh display."""
        self.tools = tools
        self.refresh()
    
    def compose(self) -> ComposeResult:
        """Compose the tools widget."""
        with Vertical():
            yield Label(
                f"Available Tools ({len(self.tools)})",
                classes="tools-title",
                id="tools-title"
            )
            
            if not self.tools:
                yield Label(
                    "No tools available",
                    classes="no-tools",
                    id="no-tools"
                )
            else:
                with VerticalScroll(id="tools-scroll"):
                    for tool in self.tools:
                        function_info = tool.get("function", {})
                        tool_name = function_info.get("name", "Unknown")
                        tool_description = function_info.get("description", "No description")
                        server_name = tool.get("_mcp_server", "Unknown")
                        
                        with Vertical(classes="tool-item"):
                            yield Label(
                                f"• {tool_name}",
                                classes="tool-name",
                                id=f"tool-name-{tool_name}"
                            )
                            yield Label(
                                f"  Server: {server_name}",
                                classes="tool-server",
                                id=f"tool-server-{tool_name}"
                            )
                            if tool_description and tool_description != "No description":
                                yield Label(
                                    f"  {tool_description}",
                                    classes="tool-description",
                                    id=f"tool-desc-{tool_name}"
                                )


class MCPStatusWidget(Widget):
    """Main MCP status display widget showing servers and tools."""
    
    DEFAULT_CSS = """
    MCPStatusWidget {
        height: auto;
        width: 100%;
        margin: 1;
        padding: 1;
        border: solid $primary;
    }
    
    .mcp-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
    }
    
    .mcp-summary {
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
    }
    
    .refresh-button {
        margin: 1;
    }
    
    .servers-section {
        margin-top: 1;
    }
    
    .tools-section {
        margin-top: 1;
    }
    
    .no-servers {
        color: $text-muted;
        text-style: italic;
        text-align: center;
        margin: 2;
    }
    """
    
    # Reactive properties for real-time updates
    server_metrics: Reactive[Dict[str, Dict[str, Any]]] = reactive({})
    available_tools: Reactive[List[Dict[str, Any]]] = reactive([])
    manager_summary: Reactive[Dict[str, Any]] = reactive({})
    
    def __init__(
        self,
        mcp_manager: MCPManager,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.mcp_manager = mcp_manager
        self._update_timer: Optional[Timer] = None
        self._server_widgets: Dict[str, MCPServerStatusWidget] = {}
        self._tools_widget: Optional[MCPToolsWidget] = None
    
    def on_mount(self) -> None:
        """Set up periodic updates when widget is mounted."""
        self._update_status()
        # Update every 5 seconds
        self._update_timer = self.set_interval(5.0, self._update_status)
        
        # Subscribe to MCP manager status changes
        self.mcp_manager.add_status_change_callback(self._on_status_change)
    
    def on_unmount(self) -> None:
        """Clean up when widget is unmounted."""
        if self._update_timer:
            self._update_timer.stop()
        
        # Unsubscribe from status changes
        self.mcp_manager.remove_status_change_callback(self._on_status_change)
    
    def _on_status_change(self, server_name: str, status: MCPConnectionStatus) -> None:
        """Handle MCP server status changes."""
        # Trigger immediate update when status changes
        self.call_later(self._update_status)
    
    async def _update_status(self) -> None:
        """Update MCP status information."""
        try:
            # Get current metrics
            self.server_metrics = self.mcp_manager.get_all_server_metrics()
            self.available_tools = await self.mcp_manager.get_available_tools()
            self.manager_summary = self.mcp_manager.get_manager_summary()
            
        except Exception as e:
            # Log error but don't crash the widget
            self.log.error(f"Error updating MCP status: {e}")
    
    def compose(self) -> ComposeResult:
        """Compose the MCP status widget."""
        with Vertical():
            # Title and summary
            yield Label(
                "MCP Server Status",
                classes="mcp-title",
                id="mcp-title"
            )
            
            # Summary information
            yield Label(
                "",  # Will be updated by watch_manager_summary
                classes="mcp-summary",
                id="mcp-summary"
            )
            
            # Refresh button
            yield Button(
                "Refresh Status",
                id="refresh-button",
                classes="refresh-button"
            )
            
            # Servers section
            with Collapsible(
                title="Servers",
                collapsed=False,
                id="servers-collapsible",
                classes="servers-section"
            ):
                with Vertical(id="servers-container"):
                    if not self.server_metrics:
                        yield Label(
                            "No MCP servers configured",
                            classes="no-servers",
                            id="no-servers"
                        )
            
            # Tools section
            with Collapsible(
                title="Available Tools",
                collapsed=True,
                id="tools-collapsible", 
                classes="tools-section"
            ):
                with Vertical(id="tools-container"):
                    pass  # Will be populated by watch_available_tools
    
    def watch_manager_summary(self, summary: Dict[str, Any]) -> None:
        """Update summary display when manager summary changes."""
        if not summary:
            return
        
        connected = summary.get("connected_servers", 0)
        total = summary.get("total_servers", 0)
        tools = summary.get("total_tools", 0)
        success_rate = summary.get("tool_success_rate", 0)
        
        summary_text = (
            f"{connected}/{total} servers connected • "
            f"{tools} tools available • "
            f"{success_rate:.1f}% tool success rate"
        )
        
        summary_label = self.query_one("#mcp-summary", Label)
        summary_label.update(summary_text)
    
    def watch_server_metrics(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """Update server widgets when metrics change."""
        servers_container = self.query_one("#servers-container", Vertical)
        
        # Remove "no servers" message if it exists
        try:
            no_servers_label = servers_container.query_one("#no-servers")
            no_servers_label.remove()
        except:
            pass
        
        # Update existing server widgets or create new ones
        current_servers = set(metrics.keys())
        existing_servers = set(self._server_widgets.keys())
        
        # Remove widgets for servers that no longer exist
        for server_name in existing_servers - current_servers:
            widget = self._server_widgets.pop(server_name)
            widget.remove()
        
        # Update or create widgets for current servers
        for server_name, server_metrics in metrics.items():
            if server_name in self._server_widgets:
                # Update existing widget
                self._server_widgets[server_name].update_metrics(server_metrics)
            else:
                # Create new widget
                widget = MCPServerStatusWidget(
                    server_name=server_name,
                    server_metrics=server_metrics,
                    id=f"server-widget-{server_name}"
                )
                self._server_widgets[server_name] = widget
                servers_container.mount(widget)
    
    def watch_available_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Update tools display when available tools change."""
        tools_container = self.query_one("#tools-container", Vertical)
        
        # Remove existing tools widget if it exists
        if self._tools_widget:
            self._tools_widget.remove()
        
        # Create new tools widget
        self._tools_widget = MCPToolsWidget(
            tools=tools,
            id="tools-widget"
        )
        tools_container.mount(self._tools_widget)
    
    @on(Button.Pressed, "#refresh-button")
    async def refresh_status(self, event: Button.Pressed) -> None:
        """Handle refresh button press."""
        await self._update_status()
        
        # Provide visual feedback
        button = event.button
        original_label = button.label
        button.label = "Refreshing..."
        button.disabled = True
        
        # Re-enable button after a short delay
        def restore_button():
            button.label = original_label
            button.disabled = False
        
        self.set_timer(1.0, restore_button)


class MCPErrorDisplay(Widget):
    """Widget for displaying MCP errors and connection issues."""
    
    DEFAULT_CSS = """
    MCPErrorDisplay {
        height: auto;
        width: 100%;
        margin: 1;
        padding: 1;
        border: solid $error;
        background: $error 10%;
    }
    
    .error-title {
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .error-message {
        color: $text;
        margin-bottom: 1;
    }
    
    .error-server {
        color: $text-muted;
        text-style: italic;
    }
    
    .dismiss-button {
        margin-top: 1;
    }
    """
    
    def __init__(
        self,
        error_message: str,
        server_name: Optional[str] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.error_message = error_message
        self.server_name = server_name
    
    def compose(self) -> ComposeResult:
        """Compose the error display widget."""
        with Vertical():
            yield Label(
                "MCP Error",
                classes="error-title",
                id="error-title"
            )
            
            yield Label(
                self.error_message,
                classes="error-message",
                id="error-message"
            )
            
            if self.server_name:
                yield Label(
                    f"Server: {self.server_name}",
                    classes="error-server",
                    id="error-server"
                )
            
            yield Button(
                "Dismiss",
                id="dismiss-button",
                classes="dismiss-button"
            )
    
    @on(Button.Pressed, "#dismiss-button")
    def dismiss_error(self, event: Button.Pressed) -> None:
        """Handle dismiss button press."""
        self.remove()


class MCPStatusIndicator(Widget):
    """Compact MCP status indicator for display in headers or sidebars."""
    
    DEFAULT_CSS = """
    MCPStatusIndicator {
        height: 1;
        width: auto;
        margin: 0 1;
    }
    
    .indicator-connected {
        color: $success;
        text-style: bold;
    }
    
    .indicator-partial {
        color: $warning;
        text-style: bold;
    }
    
    .indicator-disconnected {
        color: $error;
        text-style: bold;
    }
    
    .indicator-disabled {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    # Reactive property for status updates
    status_summary: Reactive[Dict[str, Any]] = reactive({})
    
    def __init__(
        self,
        mcp_manager: MCPManager,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.mcp_manager = mcp_manager
        self._update_timer: Optional[Timer] = None
    
    def on_mount(self) -> None:
        """Set up periodic updates when widget is mounted."""
        self._update_status()
        # Update every 10 seconds (less frequent than main widget)
        self._update_timer = self.set_interval(10.0, self._update_status)
        
        # Subscribe to MCP manager status changes
        self.mcp_manager.add_status_change_callback(self._on_status_change)
    
    def on_unmount(self) -> None:
        """Clean up when widget is unmounted."""
        if self._update_timer:
            self._update_timer.stop()
        
        # Unsubscribe from status changes
        self.mcp_manager.remove_status_change_callback(self._on_status_change)
    
    def _on_status_change(self, server_name: str, status: MCPConnectionStatus) -> None:
        """Handle MCP server status changes."""
        # Trigger immediate update when status changes
        self.call_later(self._update_status)
    
    async def _update_status(self) -> None:
        """Update MCP status summary."""
        try:
            self.status_summary = self.mcp_manager.get_manager_summary()
        except Exception as e:
            # Log error but don't crash the widget
            self.log.error(f"Error updating MCP status indicator: {e}")
    
    def compose(self) -> ComposeResult:
        """Compose the status indicator."""
        yield Label(
            "",  # Will be updated by watch_status_summary
            id="status-indicator-label"
        )
    
    def watch_status_summary(self, summary: Dict[str, Any]) -> None:
        """Update indicator display when status summary changes."""
        if not summary:
            return
        
        connected = summary.get("connected_servers", 0)
        total = summary.get("total_servers", 0)
        tools = summary.get("total_tools", 0)
        
        label = self.query_one("#status-indicator-label", Label)
        
        if total == 0:
            # No servers configured
            label.update("MCP: Disabled")
            label.remove_class("indicator-connected", "indicator-partial", "indicator-disconnected")
            label.add_class("indicator-disabled")
        elif connected == total:
            # All servers connected
            label.update(f"MCP: {connected}/{total} ({tools} tools)")
            label.remove_class("indicator-partial", "indicator-disconnected", "indicator-disabled")
            label.add_class("indicator-connected")
        elif connected > 0:
            # Some servers connected
            label.update(f"MCP: {connected}/{total} ({tools} tools)")
            label.remove_class("indicator-connected", "indicator-disconnected", "indicator-disabled")
            label.add_class("indicator-partial")
        else:
            # No servers connected
            label.update(f"MCP: {connected}/{total} (offline)")
            label.remove_class("indicator-connected", "indicator-partial", "indicator-disabled")
            label.add_class("indicator-disconnected")