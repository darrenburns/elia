from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import LoadingIndicator, Label


class AgentIsTyping(Horizontal):
    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        yield Label("  Agent is responding ")
