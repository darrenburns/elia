from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from elia_chat.models import ChatMessage


class MessageInfo(ModalScreen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close Modal")]

    def __init__(
        self,
        message: ChatMessage,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
        )
        self.message = message

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="outermost-container"):
            with Vertical(id="inner-container"):
                yield Static(self.message.get("content", ""))
