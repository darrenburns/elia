from __future__ import annotations

from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from textual.geometry import Size
from textual.reactive import reactive
from textual.widget import Widget

from elia_chat.models import ChatMessage


class Chatbox(Widget, can_focus=True):
    message: ChatMessage | None = reactive(None, init=False, always_update=True,
                                           layout=True)

    def __init__(
        self,
        message: ChatMessage | None = None,
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

    @property
    def markdown(self) -> Markdown:
        return Markdown(self.message.get("content") or "")

    def render(self) -> RenderableType:
        return self.markdown

    def get_content_width(self, container: Size, viewport: Size) -> int:
        content = self.message.get("content")
        if len(content) <= container.width or "\n" not in content:
            return len(content)
        return container.width

    def append_chunk(self, chunk: Any):
        # If this Chatbox doesn't correspond to an OpenAI message,
        # make that connection now.
        if self.message is None:
            self.message = ChatMessage(
                role="assistant",
                content="",
            )
        else:
            chunk_content = chunk["choices"][0].get("delta", {}).get("content", "")
            self.message = ChatMessage(
                role=self.message.get("role"),
                content=self.message.get("content") + chunk_content,
            )
