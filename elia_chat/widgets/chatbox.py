from __future__ import annotations
from dataclasses import dataclass

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual import on
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import TextArea
from textual.widgets.text_area import Selection

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatMessage


class SelectionTextArea(TextArea):
    @dataclass
    class LeaveSelectionMode(Message):
        pass

    BINDINGS = [
        Binding(
            "escape",
            "leave_selection_mode",
            description="Exit selection mode",
            key_display="esc",
        ),
        Binding(
            "v",
            "toggle_visual_mode",
            description="Toggle visual select",
            key_display="v",
        ),
        Binding(
            "y,c", "copy_to_clipboard", description="Copy selection", key_display="y"
        ),
    ]

    visual_mode = reactive(False, init=False)

    def action_toggle_visual_mode(self) -> None:
        self.visual_mode = not self.visual_mode

    def watch_visual_mode(self, value: bool) -> None:
        self.cursor_blink = not value

        if not value:
            self.selection = Selection.cursor(self.selection.end)

        self.set_class(value, "visual-mode")
        print(self.classes)

    def action_cursor_up(self, select: bool = False) -> None:
        return super().action_cursor_up(self.visual_mode or select)

    def action_cursor_right(self, select: bool = False) -> None:
        return super().action_cursor_right(self.visual_mode or select)

    def action_cursor_down(self, select: bool = False) -> None:
        return super().action_cursor_down(self.visual_mode or select)

    def action_cursor_left(self, select: bool = False) -> None:
        return super().action_cursor_left(self.visual_mode or select)

    def action_cursor_line_end(self, select: bool = False) -> None:
        return super().action_cursor_line_end(self.visual_mode or select)

    def action_cursor_line_start(self, select: bool = False) -> None:
        return super().action_cursor_line_start(self.visual_mode or select)

    def action_cursor_word_left(self, select: bool = False) -> None:
        return super().action_cursor_word_left(self.visual_mode or select)

    def action_cursor_word_right(self, select: bool = False) -> None:
        return super().action_cursor_word_right(self.visual_mode or select)

    def action_copy_to_clipboard(self) -> None:
        text_to_copy = self.selected_text
        if text_to_copy:
            message = f"Copied {len(text_to_copy)} selected characters to clipboard."
            self.notify(message, title="Selection copied")
        else:
            text_to_copy = self.text
            message = f"Copied message ({len(text_to_copy)} characters)."
            self.notify(message, title="Message copied")

        self.app.copy_to_clipboard(text_to_copy)
        self.visual_mode = False

    def action_leave_selection_mode(self) -> None:
        self.post_message(self.LeaveSelectionMode())


class Chatbox(Widget, can_focus=True):
    BINDINGS = [
        Binding(key="up,k", action="up", description="Up", show=False),
        Binding(key="down,j", action="down", description="Down", show=False),
        Binding(key="enter", action="select", description="Toggle select mode"),
        Binding(
            key="y,c",
            action="copy_to_clipboard",
            description="Copy full message",
            key_display="y",
        ),
        Binding(
            key="escape",
            action="screen.focus('prompt')",
            description="Focus prompt",
            key_display="esc",
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
        if not self.selection_mode:
            text_to_copy = self.message.message.get("content")
            if isinstance(text_to_copy, str):
                self.app.copy_to_clipboard(text_to_copy)
                message = f"Copied message ({len(text_to_copy)} characters)."
                self.notify(message, title="Message copied")
            else:
                message = "Unable to copy message"
                self.notify(message, title="Clipboard error", severity="error")

    async def watch_selection_mode(self, value: bool) -> None:
        if value:
            async with self.batch():
                self.border_subtitle = "[[white]c[/]] Copy selection"
                content = self.message.message.get("content")
                text_area = SelectionTextArea(
                    content if isinstance(content, str) else "",
                    read_only=True,
                    language="markdown",
                    classes="selection-mode",
                )
                await self.mount(text_area)
                text_area._rewrap_and_refresh_virtual_size()
                text_area.focus(scroll_visible=False)
        else:
            self.border_subtitle = ""
            try:
                self.query_one(SelectionTextArea)
            except NoMatches:
                # Shouldn't happen, but let's be defensive.
                self.log.warning("In selection mode, but no text area found.")
                pass
            else:
                await self.remove_children()

    @on(SelectionTextArea.LeaveSelectionMode)
    def leave_selection_mode(self) -> None:
        self.selection_mode = False

    def watch_has_focus(self, value: bool) -> None:
        if value:
            try:
                child = self.query_one(SelectionTextArea)
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
            # When in selection mode, this widget has a SelectionTextArea child,
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
