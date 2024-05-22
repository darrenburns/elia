from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input


class RenameChat(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel", key_display="esc"),
        Binding("enter", "app.pop_screen", "Save"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            title_input = Input(placeholder="Enter a title...")
            title_input.border_subtitle = (
                "[[white]enter[/]] Save  [[white]esc[/]] Cancel"
            )
            yield title_input

    @on(Input.Submitted)
    def close_screen(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
