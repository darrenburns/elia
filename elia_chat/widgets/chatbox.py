from __future__ import annotations
import html

from langchain_core.messages import BaseMessage
from rich.console import RenderableType
from rich.markdown import Markdown
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.geometry import Size
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import TextArea

from elia_chat.screens.message_info_modal import MessageInfo


class Chatbox(Widget, can_focus=True):
    BINDINGS = [
        Binding(key="enter", action="details", description="Message details"),
        Binding(key="up,k", action="up", description="Up"),
        Binding(key="down,j", action="down", description="Down"),
        Binding(key="space", action="select", description="Toggle Select"),
        Binding(
            key="c",
            action="copy_to_clipboard",
            description="Copy selection to clipboard",
            show=False,
        ),
    ]

    selection_mode = reactive(False, init=False)

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

    def action_select(self) -> None:
        self.selection_mode = not self.selection_mode
        self.set_class(self.selection_mode, "selecting")

    def action_copy_to_clipboard(self) -> None:
        if self.selection_mode:
            try:
                text_area = self.query_one(TextArea)
            except NoMatches:
                return
            text_to_copy = text_area.selected_text
            if text_to_copy:
                message = f"Copied {len(text_to_copy)} selected characters."
            else:
                text_to_copy = text_area.text
                message = f"Copied message ({len(text_to_copy)} characters)."
        else:
            text_to_copy = self.message.content
            message = f"Copied message ({len(text_to_copy)} characters)."

        self.app.copy_to_clipboard(text_to_copy)
        self.notify(message, title="Clipboard")
        self.selection_mode = False

    async def watch_selection_mode(self, value: bool) -> None:
        if value:
            self.border_subtitle = "[[white]c[/]] Copy selection"
            text_area = TextArea(
                self.message.content,
                read_only=True,
                language="markdown",
                classes="selection-mode",
            )
            await self.mount(text_area)
            text_area._rewrap_and_refresh_virtual_size()
            text_area.focus()
        else:
            self.border_subtitle = ""
            try:
                self.query_one(TextArea)
            except NoMatches:
                # Shouldn't happen, but let's be defensive.
                pass
            else:
                await self.remove_children()

        self.scroll_visible(animate=False, top=True)

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
