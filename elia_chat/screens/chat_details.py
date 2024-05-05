from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from elia_chat.models import ChatData


class ChatDetails(ModalScreen[None]):
    BINDINGS = [
        Binding(
            "escape",
            "app.pop_screen",
            "Close",
        )
    ]

    def __init__(
        self,
        chat: ChatData,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.chat = chat

    def compose(self) -> ComposeResult:
        chat = self.chat

        content = chat.system_prompt.message.get("content", "")
        if isinstance(content, str):
            yield Label("[b]System prompt")
            yield Markdown(content)
