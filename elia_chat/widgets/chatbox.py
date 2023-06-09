from __future__ import annotations

import time
from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from textual.binding import Binding
from textual.geometry import Size
from textual.widget import Widget

from elia_chat.models import ChatMessage
from elia_chat.screens.message_info_modal import MessageInfo
from elia_chat.time_display import format_timestamp


class Chatbox(Widget, can_focus=True):
    BINDINGS = [Binding(key="d", action="details", description="Message details")]

    def __init__(
        self,
        message: ChatMessage,
        model_name: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.message = message
        self.model_name = model_name
        timestamp = format_timestamp(message.get("timestamp", 0) or 0)
        self.tooltip = f"Sent {timestamp}"

    def on_mount(self) -> None:
        if self.message.get("role") == "assistant":
            self.add_class("assistant-message")

    def action_details(self) -> None:
        self.app.push_screen(
            MessageInfo(message=self.message, model_name=self.model_name)
        )

    @property
    def markdown(self) -> Markdown:
        return Markdown(self.message.get("content") or "")

    def render(self) -> RenderableType:
        return self.markdown

    def get_content_width(self, container: Size, viewport: Size) -> int:
        # Naive approach. Can sometimes look strange, but works well enough.
        content = self.message.get("content", "")
        return min(len(content), container.width)

    def append_chunk(self, chunk: Any):
        # If this Chatbox doesn't correspond to an OpenAI message,
        # make that connection now.
        if self.message.get("content") is None:
            # TODO - fill in the None values below
            self.message = ChatMessage(
                id=None,
                role="assistant",
                content="",
                timestamp=time.time(),
                status=None,
                end_turn=None,
                weight=None,
                metadata=None,
                recipient=None,
            )
        else:
            chunk_content = chunk["choices"][0].get("delta", {}).get("content", "")
            self.message = ChatMessage(
                id=None,
                role=self.message.get("role", "undefined"),
                content=self.message.get("content", "") + chunk_content,
                timestamp=time.time(),
                status=None,
                end_turn=None,
                weight=None,
                metadata=None,
                recipient=None,
            )
        self.refresh(layout=True)
