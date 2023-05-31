from __future__ import annotations

from datetime import datetime

import tiktoken
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Tabs, ContentSwitcher, Tab

from elia_chat.models import ChatMessage
from elia_chat.widgets.token_analysis import TokenAnalysis


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
        markdown_content = self.message.get("content", "")
        encoder = tiktoken.encoding_for_model(self.model_name)
        tokens = encoder.encode(markdown_content)

        with Vertical(id="outermost-container"):
            with Horizontal(id="message-info-header"):
                yield Tabs(
                    Tab("Markdown", id="markdown-content"),
                    Tab("Tokens", id="tokens"),
                    Tab("Metadata", id="metadata"),
                )

            with VerticalScroll(id="inner-container"):
                with ContentSwitcher(initial="markdown-content"):
                    yield Static(markdown_content, id="markdown-content")
                    yield TokenAnalysis(tokens, encoder, id="tokens")
                    yield Static("Metadata", id="metadata")

            with Horizontal(id="message-info-footer"):
                if self.model_name:
                    token_count = len(tokens)

                timestamp = self.message.get("timestamp") or 0
                timestamp_string = datetime.utcfromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                yield Static(f"Message sent at {timestamp_string}", id="timestamp")
                yield Static(f"{token_count} tokens", id="token-count")

    @on(Tabs.TabActivated)
    def tab_activated(self, event: Tabs.TabActivated) -> None:
        self.query_one(ContentSwitcher).current = event.tab.id
