from __future__ import annotations
import html

from langchain.schema import BaseMessage
from rich.console import RenderableType
from rich.markdown import Markdown
from textual.binding import Binding
from textual.geometry import Size
from textual.widget import Widget

from elia_chat.screens.message_info_modal import MessageInfo


class Chatbox(Widget, can_focus=True):
    BINDINGS = [
        Binding(key="enter", action="details", description="Message details"),
        Binding(key="up,k", action="up", description="Up"),
        Binding(key="down,j", action="down", description="Down"),
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

    def on_mount(self) -> None:
        if self.message.type == "ai":
            self.add_class("assistant-message")
            self.border_title = "Agent"
        else:
            self.add_class("human-message")
            self.border_title = "You"

    def action_up(self) -> None:
        self.screen.focus_previous(Chatbox)

    def action_down(self) -> None:
        self.screen.focus_next(Chatbox)

    def action_details(self) -> None:
        self.app.push_screen(
            MessageInfo(message=self.message, model_name=self.model_name)
        )

    @property
    def markdown(self) -> Markdown:
        message = self.message
        if message.type == "human":
            content = html.escape(message.content)
        else:
            content = message.content
        return Markdown(content)

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
