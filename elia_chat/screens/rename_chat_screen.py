from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input


class RenameChat(ModalScreen[str]):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close window")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="Enter a new title...")

    @on(Input.Submitted)
    def close_screen(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
