from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import Reactive, reactive
from textual.widgets import LoadingIndicator, Label


class ResponseStatus(Vertical):
    """
    A widget that displays the status of the response from the agent.
    """

    message: Reactive[str] = reactive("Agent is responding", recompose=True)

    def compose(self) -> ComposeResult:
        yield Label(f" {self.message}")
        yield LoadingIndicator()

    def set_awaiting_response(self) -> None:
        self.message = "Awaiting response"
        self.add_class("-awaiting-response")
        self.remove_class("-agent-responding")

    def set_agent_responding(self) -> None:
        self.message = "Agent is responding"
        self.add_class("-agent-responding")
        self.remove_class("-awaiting-response")
