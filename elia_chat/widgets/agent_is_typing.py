from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import LoadingIndicator, Label


class AgentIsTyping(Widget):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield LoadingIndicator()
            yield Label("  Agent is responding ")
