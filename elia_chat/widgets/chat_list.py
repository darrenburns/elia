from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import cast

import humanize
from rich.console import RenderResult, Console, ConsoleOptions
from rich.markup import escape
from rich.padding import Padding
from rich.text import Text
from textual import events, log, on
from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from elia_chat.chats_manager import ChatsManager
from elia_chat.config import LaunchConfig
from elia_chat.models import ChatData


@dataclass
class ChatListItemRenderable:
    chat: ChatData
    config: LaunchConfig

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - self.chat.update_time
        time_ago = humanize.naturaltime(delta)
        time_ago_text = Text(time_ago, style="dim i")
        model = self.chat.model
        subtitle = f"[dim]{escape(model.display_name or model.name)}"
        if model.provider:
            subtitle += f" [i]by[/] {escape(model.provider)}"
        model_text = Text.from_markup(subtitle)
        title = self.chat.title or self.chat.short_preview.replace("\n", " ")
        yield Padding(
            Text.assemble(title, "\n", model_text, "\n", time_ago_text),
            pad=(0, 0, 0, 1),
        )


class ChatListItem(Option):
    def __init__(self, chat: ChatData, config: LaunchConfig) -> None:
        """
        Args:
            chat: The chat associated with this option.
        """
        super().__init__(ChatListItemRenderable(chat, config))
        self.chat = chat
        self.config = config


class ChatList(OptionList):
    BINDINGS = [
        Binding(
            "escape", "app.focus('home-prompt')", "Focus prompt", key_display="esc"
        ),
        Binding("a", "archive_chat", "Archive chat", key_display="a"),
        Binding("j,down", "cursor_down", "Down", show=False),
        Binding("k,up", "cursor_up", "Up", show=False),
        Binding("l,right,enter", "select", "Select", show=False),
        Binding("g,home", "first", "First", show=False),
        Binding("G,end", "last", "Last", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
    ]

    @dataclass
    class ChatOpened(Message):
        chat: ChatData

    class CursorEscapingTop(Message):
        """Cursor attempting to move out-of-bounds at top of list."""

    class CursorEscapingBottom(Message):
        """Cursor attempting to move out-of-bounds at bottom of list."""

    async def on_mount(self) -> None:
        await self.reload_and_refresh()

    @on(OptionList.OptionSelected)
    async def post_chat_opened(self, event: OptionList.OptionSelected) -> None:
        assert isinstance(event.option, ChatListItem)
        chat = event.option.chat
        await self.reload_and_refresh()
        self.post_message(ChatList.ChatOpened(chat=chat))

    @on(OptionList.OptionHighlighted)
    @on(events.Focus)
    def show_border_subtitle(self) -> None:
        if self.highlighted is not None:
            self.border_subtitle = "[[white]Enter[/]] Open chat"
        elif self.option_count > 0:
            self.highlighted = 0

    def on_blur(self) -> None:
        self.border_subtitle = None

    async def reload_and_refresh(self, new_highlighted: int = -1) -> None:
        """Reload the chats and refresh the widget. Can be used to
        update the ordering/previews/titles etc contained in the list.

        Args:
            new_highlighted: The index to highlight after refresh.
        """
        self.options = await self.load_chat_list_items()
        old_highlighted = self.highlighted
        self.clear_options()
        self.add_options(self.options)
        self.border_title = self.get_border_title()
        if new_highlighted > -1:
            self.highlighted = new_highlighted
        else:
            self.highlighted = old_highlighted

    async def load_chat_list_items(self) -> list[ChatListItem]:
        chats = await self.load_chats()
        return [ChatListItem(chat, self.app.launch_config) for chat in chats]

    async def load_chats(self) -> list[ChatData]:
        all_chats = await ChatsManager.all_chats()
        return all_chats

    async def action_archive_chat(self) -> None:
        if self.highlighted is None:
            return

        item = cast(ChatListItem, self.get_option_at_index(self.highlighted))
        self.options.pop(self.highlighted)
        self.remove_option_at_index(self.highlighted)

        chat_id = item.chat.id
        await ChatsManager.archive_chat(chat_id)

        self.border_title = self.get_border_title()
        self.refresh()
        self.app.notify(f"Chat [b]{chat_id!r}[/] archived")

    def get_border_title(self) -> str:
        return f"History ({len(self.options)})"

    def create_chat(self, chat_data: ChatData) -> None:
        new_chat_list_item = ChatListItem(chat_data, self.app.launch_config)
        log.debug(f"Creating new chat {new_chat_list_item!r}")

        option_list = self.query_one(OptionList)
        self.options = [
            new_chat_list_item,
            *self.options,
        ]
        option_list.clear_options()
        option_list.add_options(self.options)
        option_list.highlighted = 0
        self.refresh()

    def action_cursor_up(self) -> None:
        if self.highlighted == 0:
            self.post_message(self.CursorEscapingTop())
        else:
            return super().action_cursor_up()
