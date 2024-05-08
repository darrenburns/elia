from __future__ import annotations

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.geometry import Size
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import TextArea

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatMessage


class Chatbox(Widget, can_focus=True):
    BINDINGS = [
        Binding(key="up,k", action="up", description="Up"),
        Binding(key="down,j", action="down", description="Down"),
        Binding(key="space", action="select", description="Toggle select mode"),
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
        message: ChatMessage,
        model: EliaChatModel,
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
        self.model = model

    def on_mount(self) -> None:
        litellm_message = self.message.message
        role = litellm_message["role"]
        if role == "assistant":
            self.add_class("assistant-message")
            self.border_title = "Agent"
        else:
            self.add_class("human-message")
            self.border_title = "You"

    def action_up(self) -> None:
        self.screen.focus_previous(Chatbox)

    def action_down(self) -> None:
        self.screen.focus_next(Chatbox)

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
            text_to_copy = self.message.message.get("content")
            if isinstance(text_to_copy, str):
                message = f"Copied message ({len(text_to_copy)} characters)."
            else:
                message = "Unable to copy message"

        if isinstance(text_to_copy, str):
            self.app.copy_to_clipboard(text_to_copy)
            self.notify(message, title="Clipboard")
        else:
            self.notify(message, title="Clipboard", severity="error")

        self.selection_mode = False

    async def watch_selection_mode(self, value: bool) -> None:
        if value:
            self.border_subtitle = "[[white]c[/]] Copy selection"
            content = self.message.message.get("content")
            text_area = TextArea(
                content if isinstance(content, str) else "",
                read_only=True,
                language="markdown",
                classes="selection-mode",
            )
            async with self.batch():
                await self.mount(text_area)
                text_area._rewrap_and_refresh_virtual_size()
                text_area.focus(scroll_visible=False)
        else:
            self.border_subtitle = ""
            try:
                self.query_one(TextArea)
            except NoMatches:
                # Shouldn't happen, but let's be defensive.
                pass
            else:
                await self.remove_children()

    def watch_has_focus(self, value: bool) -> None:
        if value:
            try:
                child = self.query_one(TextArea)
            except NoMatches:
                return None
            else:
                child.focus()

    @property
    def markdown(self) -> Markdown:
        """Return the content as a Rich Markdown object."""
        content = self.message.message.get("content")
        if not isinstance(content, str):
            content = ""
        return Markdown(content)

    def render(self) -> RenderableType:
        if self.selection_mode:
            # When in selection mode, this widget has a TextArea child,
            # so we do not need to render anything.
            return ""

        message = self.message.message
        if message["role"] == "user":
            content = message["content"] or ""
            if isinstance(content, str):
                return Syntax(
                    content,
                    lexer="markdown",
                    word_wrap=True,
                    background_color="#121212",
                )
            else:
                return ""
        return self.markdown

    def get_content_width(self, container: Size, viewport: Size) -> int:
        # Naive approach. Can sometimes look strange, but works well enough.
        content = self.message.message.get("content")
        if isinstance(content, str):
            content_width = min(len(content), container.width)
        else:
            content_width = 10  # Arbitrary
        return content_width

    def append_chunk(self, chunk: str) -> None:
        """Append a chunk of text to the end of the message."""
        content = self.message.message.get("content")
        if isinstance(content, str):
            content += chunk
            self.message.message["content"] = content
            self.refresh(layout=True)
