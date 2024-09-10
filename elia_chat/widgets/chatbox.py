from __future__ import annotations
import bisect
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
from textual.document._syntax_aware_document import SyntaxAwareDocumentError

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatMessage


class SelectionTextArea(TextArea):
    class LeaveSelectionMode(Message):
        """Broadcast that the user wants to leave selection mode."""

    @dataclass
    class VisualModeToggled(Message):
        """Sent when we enter/leave visual select mode."""

        enabled: bool

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
        Binding("up,k", "cursor_up", "Cursor Up", show=False),
        Binding("down,j", "cursor_down", "Cursor Down", show=False),
        Binding("right,l", "cursor_right", "Cursor Right", show=False),
        Binding("left,h", "cursor_left", "Cursor Left", show=False),
        Binding("shift+up,K", "cursor_up(True)", "cursor up select", show=False),
        Binding("shift+down,J", "cursor_down(True)", "cursor down select", show=False),
        Binding("shift+left,H", "cursor_left(True)", "cursor left select", show=False),
        Binding(
            "shift+right,L", "cursor_right(True)", "cursor right select", show=False
        ),
        Binding("ctrl+left,b", "cursor_word_left", "cursor word left", show=False),
        Binding("ctrl+right,w", "cursor_word_right", "cursor word right", show=False),
        Binding(
            "home,ctrl+a,0,^", "cursor_line_start", "cursor line start", show=False
        ),
        Binding("end,ctrl+e,$", "cursor_line_end", "cursor line end", show=False),
        Binding("pageup,ctrl+b", "cursor_page_up", "cursor page up", show=False),
        Binding("pagedown,ctrl+f", "cursor_page_down", "cursor page down", show=False),
        Binding("ctrl+d", "cursor_half_page_down", "cursor half page down", show=False),
        Binding("ctrl+u", "cursor_half_page_up", "cursor half page up", show=False),
        Binding(
            "ctrl+shift+left,B",
            "cursor_word_left(True)",
            "cursor left word select",
            show=False,
        ),
        Binding(
            "ctrl+shift+right,W",
            "cursor_word_right(True)",
            "cursor right word select",
            show=False,
        ),
        Binding("f6,V", "select_line", "select line", show=False),
        Binding(
            "y,c",
            "copy_to_clipboard",
            description="Copy selection",
            show=False,
        ),
        Binding("g", "cursor_top", "Go to top", show=False),
        Binding("G", "cursor_bottom", "Go to bottom", show=False),
        Binding("u", "next_code_block", description="Next code block", key_display="u"),
    ]

    visual_mode = reactive(False, init=False)

    def action_toggle_visual_mode(self) -> None:
        self.visual_mode = not self.visual_mode

    def watch_visual_mode(self, value: bool) -> None:
        self.post_message(self.VisualModeToggled(value))
        self.cursor_blink = not value

        if not value:
            self.selection = Selection.cursor(self.selection.end)

        self.set_class(value, "visual-mode")

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

    def action_cursor_top(self) -> None:
        self.selection = Selection.cursor((0, 0))

    def action_cursor_bottom(self) -> None:
        self.selection = Selection.cursor((self.document.line_count - 1, 0))

    def action_copy_to_clipboard(self) -> None:
        text_to_copy = self.selected_text

        if text_to_copy:
            message = f"Copied {len(text_to_copy)} selected characters to clipboard."
            title = "Selection copied"
        else:
            text_to_copy = self.text
            message = f"Copied message ({len(text_to_copy)} characters)."
            title = "Message copied"

        try:
            import pyperclip

            pyperclip.copy(text_to_copy)
        except pyperclip.PyperclipException as exc:
            self.notify(
                str(exc),
                title="Clipboard error",
                severity="error",
                timeout=10,
            )
        else:
            self.notify(message, title=title)

        self.visual_mode = False

    def action_next_code_block(self) -> None:
        try:
            query = self.document.prepare_query(
                "(fenced_code_block (code_fence_content) @code_block)"
            )
        except SyntaxAwareDocumentError:
            self.app.notify(
                "This feature requires tree-sitter, which isn't installed.",
                severity="error",
            )
        else:
            if query:
                code_block_nodes = self.document.query_syntax_tree(query)
                locations: list[tuple[tuple[int, int], tuple[int, int]]] = [
                    (node.start_point, node.end_point)
                    for (node, _name) in code_block_nodes
                ]
                if not locations:
                    return
                self.visual_mode = True
                end_locations = [end for _start, end in locations]
                cursor_row, _cursor_column = self.cursor_location
                search_start_location = cursor_row + 1, 0
                insertion_index = bisect.bisect_left(
                    end_locations, search_start_location
                )
                insertion_index %= len(end_locations)
                start, end = locations[insertion_index]
                self.selection = Selection(start, end)

    def action_leave_selection_mode(self) -> None:
        self.post_message(self.LeaveSelectionMode())

    def action_cursor_half_page_down(self) -> None:
        """Move the cursor and scroll down half of a page."""
        half_height = self.content_size.height // 2
        _, cursor_location = self.selection
        target = self.navigator.get_location_at_y_offset(
            cursor_location,
            half_height,
        )
        self.scroll_relative(y=half_height, animate=False)
        self.move_cursor(target)

    def action_cursor_half_page_up(self) -> None:
        """Move the cursor and scroll down half of a page."""
        half_height = self.content_size.height // 2
        _, cursor_location = self.selection
        target = self.navigator.get_location_at_y_offset(
            cursor_location,
            -half_height,
        )
        self.scroll_relative(y=-half_height, animate=False)
        self.move_cursor(target)


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

    class CursorEscapingBottom(Message):
        """Sent when the cursor moves down from the bottom message."""

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
        if self.parent and self is self.parent.children[-1]:
            self.post_message(self.CursorEscapingBottom())
        else:
            self.screen.focus_next(Chatbox)

    def action_select(self) -> None:
        self.selection_mode = not self.selection_mode
        self.set_class(self.selection_mode, "selecting")

    def action_copy_to_clipboard(self) -> None:
        if not self.selection_mode:
            text_to_copy = self.message.message.get("content")
            if isinstance(text_to_copy, str):
                try:
                    import pyperclip

                    pyperclip.copy(text_to_copy)
                except pyperclip.PyperclipException as exc:
                    self.notify(
                        str(exc),
                        title="Clipboard error",
                        severity="error",
                        timeout=10,
                    )
                else:
                    message = f"Copied message ({len(text_to_copy)} characters)."
                    self.notify(message, title="Message copied")
            else:
                message = "Unable to copy message"
                self.notify(message, title="Clipboard error", severity="error")

    async def watch_selection_mode(self, value: bool) -> None:
        if value:
            async with self.batch():
                self.border_subtitle = "SELECT"
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

    @on(SelectionTextArea.VisualModeToggled)
    def handle_visual_select(self, event: SelectionTextArea.VisualModeToggled) -> None:
        self.border_subtitle = (
            "[reverse] VISUAL SELECT [/]" if event.enabled else "SELECT"
        )

    @property
    def markdown(self) -> Markdown:
        """Return the content as a Rich Markdown object."""
        content = self.message.message.get("content")
        if not isinstance(content, str):
            content = ""

        return Markdown(content, code_theme=self.app.launch_config.message_code_theme)

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
