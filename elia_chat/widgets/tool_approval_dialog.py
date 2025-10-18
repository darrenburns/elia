"""Tool approval dialog for MCP tool execution."""

import json
from typing import Dict, Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ToolApprovalDialog(ModalScreen[bool]):
    """Modal dialog for approving MCP tool execution."""
    
    BINDINGS = [
        Binding("y", "approve", "Approve", key_display="y"),
        Binding("n", "deny", "Deny", key_display="n"),
        Binding("escape", "deny", "Cancel", key_display="esc"),
    ]
    
    def __init__(self, tool_name: str, arguments: Dict[str, Any], server_name: Optional[str] = None):
        """Initialize tool approval dialog.
        
        Args:
            tool_name: Name of the tool requesting approval
            arguments: Tool arguments
            server_name: Name of the MCP server providing the tool
        """
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments
        self.server_name = server_name
    
    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Vertical(id="tool-approval-dialog"):
            yield Label("Tool Approval Required", id="dialog-title")
            
            with Vertical(id="tool-info"):
                yield Label(f"Tool: {self.tool_name}", classes="tool-name")
                
                if self.server_name:
                    yield Label(f"Server: {self.server_name}", classes="server-name")
                
                if self.arguments:
                    args_text = json.dumps(self.arguments, indent=2)
                    yield Label("Arguments:", classes="arguments-label")
                    yield Static(args_text, id="arguments-display")
                else:
                    yield Label("No arguments", classes="no-arguments")
            
            yield Label(
                "Do you want to allow this tool to execute?",
                id="approval-question"
            )
            
            with Horizontal(id="button-container"):
                yield Button("Approve", variant="success", id="approve-btn")
                yield Button("Deny", variant="error", id="deny-btn")
    
    @on(Button.Pressed, "#approve-btn")
    def approve_tool(self) -> None:
        """Approve tool execution."""
        self.dismiss(True)
    
    @on(Button.Pressed, "#deny-btn") 
    def deny_tool(self) -> None:
        """Deny tool execution."""
        self.dismiss(False)
    
    def action_approve(self) -> None:
        """Approve tool execution via keybinding."""
        self.dismiss(True)
    
    def action_deny(self) -> None:
        """Deny tool execution via keybinding."""
        self.dismiss(False)