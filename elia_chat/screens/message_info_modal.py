from __future__ import annotations
import datetime
from typing import cast

import tiktoken
from langchain.schema import BaseMessage
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Tabs, ContentSwitcher, Tab, TextArea

from elia_chat.time_display import format_timestamp
from elia_chat.widgets.token_analysis import TokenAnalysis


class MessageInfo(ModalScreen[None]):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close Modal")]

    def __init__(
        self,
        message: BaseMessage,
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
        markdown_content = self.message.content or ""
        encoder = tiktoken.encoding_for_model(self.model_name)
        tokens = encoder.encode(markdown_content)

        with Vertical(id="outermost-container"):
            with Horizontal(id="message-info-header"):
                yield Tabs(
                    Tab("Markdown", id="markdown-content"),
                    Tab("Tokens", id="tokens"),
                    Tab("Metadata", id="metadata"),
                )

            with Vertical(id="inner-container"):
                with ContentSwitcher(initial="markdown-content"):
                    text_area = TextArea(
                        markdown_content,
                        read_only=True,
                        show_line_numbers=True,
                        id="markdown-content",
                    )
                    text_area.border_subtitle = "read-only"
                    yield text_area
                    yield TokenAnalysis(tokens, encoder, id="tokens")
                    yield Static("Metadata", id="metadata")

            with Horizontal(id="message-info-footer"):
                if self.model_name:
                    token_count = len(tokens)

                timestamp = cast(
                    datetime.datetime,
                    self.message.additional_kwargs.get("timestamp", 0.0),
                )
                timestamp_string = format_timestamp(timestamp if timestamp else 0.0)
                yield Static(f"Message sent at {timestamp_string}", id="timestamp")
                yield Static(f"{token_count} tokens", id="token-count")

    @on(Tabs.TabActivated)
    def tab_activated(self, event: Tabs.TabActivated) -> None:
        self.query_one(ContentSwitcher).current = event.tab.id
