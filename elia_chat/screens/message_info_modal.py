from __future__ import annotations
import datetime
from typing import TYPE_CHECKING, cast

import tiktoken
from langchain_core.messages import BaseMessage
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Footer, Static, Tabs, ContentSwitcher, Tab, TextArea

from elia_chat.models import get_model_by_name
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.time_display import format_timestamp
from elia_chat.widgets.token_analysis import TokenAnalysis

if TYPE_CHECKING:
    from elia_chat.app import Elia


class MessageInfo(ModalScreen[RuntimeConfig]):
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
        self.elia = cast("Elia", self.app)

    def compose(self) -> ComposeResult:
        markdown_content = self.message.content or ""
        model = get_model_by_name(self.model_name, self.elia.launch_config)
        if model.provider == "openai":
            encoder = tiktoken.encoding_for_model(self.model_name)
            tokens = encoder.encode(markdown_content)
        else:
            encoder, tokens = None, None
        with Vertical(id="outermost-container"):
            with Horizontal(id="message-info-header"):
                with Tabs():
                    yield Tab("Markdown", id="markdown-content")
                    if model.provider == "openai":
                        yield Tab("Tokens", id="tokens")
                    yield Tab("Metadata", id="metadata")

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
                    if (
                        model.provider == "openai"
                        and tokens is not None
                        and encoder is not None
                    ):
                        yield TokenAnalysis(tokens, encoder, id="tokens")
                    yield Static("Metadata", id="metadata")

            with Horizontal(id="message-info-footer"):
                timestamp = cast(
                    datetime.datetime,
                    self.message.additional_kwargs.get("timestamp"),
                )
                if timestamp:
                    timestamp_string = format_timestamp(timestamp if timestamp else 0.0)
                    yield Static(f"Message sent at {timestamp_string}", id="timestamp")

                if tokens is not None:
                    yield Static(f"{len(tokens)} tokens", id="token-count")

        yield Footer()

    @on(Tabs.TabActivated)
    def tab_activated(self, event: Tabs.TabActivated) -> None:
        self.query_one(ContentSwitcher).current = event.tab.id
