from __future__ import annotations

import pyperclip
from langchain.schema import BaseMessage
from rich.console import RenderableType
from rich.markdown import Markdown
from textual.binding import Binding
from textual.geometry import Size
from textual.widget import Widget

from elia_chat.screens.message_info_modal import MessageInfo
from elia_chat.time_display import format_timestamp


class Chatbox(Widget, can_focus=True):
    BINDINGS = [
        Binding(key="d", action="details", description="Message details"),
        Binding(key="c", action="copy_to_clipboard", description="Copy Content"),
    ]

    def __init__(
        self,
        message: BaseMessage,
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
        timestamp = format_timestamp(message.additional_kwargs.get("timestamp", 0) or 0)
        self.tooltip = f"Sent {timestamp}"

    def on_mount(self) -> None:
        if self.message.type == "ai":
            self.add_class("assistant-message")

    def action_details(self) -> None:
        self.app.push_screen(
            MessageInfo(message=self.message, model_name=self.model_name)
        )

    @property
    def markdown(self) -> Markdown:
        return Markdown(self.message.content or "")

    def render(self) -> RenderableType:
        return self.markdown

    def get_content_width(self, container: Size, viewport: Size) -> int:
        # Naive approach. Can sometimes look strange, but works well enough.
        content = self.message.content or ""
        return min(len(content), container.width)

    def append_chunk(self, chunk: str):
        existing_content = self.message.content or ""
        new_content = existing_content + chunk
        self.message.content = new_content
        self.refresh(layout=True)

    def action_copy_to_clipboard(self):
        content_to_copy = self.message.content or ""
        pyperclip.copy(content_to_copy)
