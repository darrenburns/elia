from __future__ import annotations

from datetime import datetime

import tiktoken
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Tabs

from elia_chat.models import ChatMessage


class MessageInfo(ModalScreen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close Modal")]

    def __init__(
        self,
        message: ChatMessage,
        model_name: str,
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
        self.model_name = model_name

    def compose(self) -> ComposeResult:
        content = self.message.get("content", "")

        with Vertical(id="outermost-container"):
            with Horizontal(id="message-info-header"):
                yield Tabs("Markdown", "Tokens", "Metadata")

            with VerticalScroll():
                with Vertical(id="inner-container"):
                    yield Static(content)

            with Horizontal(id="message-info-footer"):
                if self.model_name:
                    encoder = tiktoken.encoding_for_model(self.model_name)
                    token_count = len(encoder.encode(content))

                timestamp = self.message.get("timestamp") or 0
                timestamp_string = datetime.utcfromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                yield Static(f"Message sent at {timestamp_string}", id="timestamp")
                yield Static(f"{token_count} tokens", id="token-count")
