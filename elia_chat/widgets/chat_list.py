from __future__ import annotations

import datetime
from dataclasses import dataclass

import humanize
from rich.console import RenderResult, Console, ConsoleOptions
from rich.padding import Padding
from rich.text import Text
from textual import events, log, on
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData


@dataclass
class ChatListItemRenderable:
    chat: ChatData
    is_open: bool = False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        utc_dt = datetime.datetime.now(datetime.UTC)
        local_dt = utc_dt.astimezone()
        delta = local_dt - self.chat.create_time
        subtitle = humanize.naturaltime(delta)
        yield Padding(
            Text.assemble(
                (self.chat.short_preview, "" if not self.is_open else "b"),
                "\n",
                (subtitle, "dim"),
            ),
            pad=(0, 1),
        )


class ChatListItem(Option):
    def __init__(self, chat: ChatData, is_open: bool = False) -> None:
        """
        Args:
            chat: The chat associated with this option.
            is_open: True if this is the chat that's currently open.
        """
        super().__init__(ChatListItemRenderable(chat, is_open=is_open))
        self.chat = chat
        self.is_open = is_open


class ChatList(OptionList):
    current_chat_id: reactive[str | None] = reactive(None)

    @dataclass
    class ChatOpened(Message):
        chat: ChatData

    def on_mount(self) -> None:
        self.border_title = "Chat history"
        self.options = self.load_chat_list_items()
        self.add_options(self.options)

    @on(OptionList.OptionSelected)
    def post_chat_opened(self, event: OptionList.OptionSelected) -> None:
        assert isinstance(event.option, ChatListItem)
        chat = event.option.chat
        self.current_chat_id = chat.id
        self.reload_and_refresh()
        self.post_message(ChatList.ChatOpened(chat=chat))

    @on(OptionList.OptionHighlighted)
    @on(events.Focus)
    def show_border_subtitle(self) -> None:
        if self.highlighted is not None:
            self.border_subtitle = "[[white]Enter[/]] Open Chat"

    def on_blur(self) -> None:
        self.border_subtitle = None

    def reload_and_refresh(self, new_highlighted: int = -1) -> None:
        """Reload the chats and refresh the widget. Can be used to
        update the ordering/previews/titles etc contained in the list.

        Args:
            new_highlighted: The index to highlight after refresh.
        """
        self.options = self.load_chat_list_items()
        old_highlighted = self.highlighted
        self.clear_options()
        self.add_options(self.options)
        if new_highlighted > -1:
            self.highlighted = new_highlighted
        else:
            self.highlighted = old_highlighted

    def load_chat_list_items(self) -> list[ChatListItem]:
        chats = self.load_chats()
        return [
            ChatListItem(chat, is_open=self.current_chat_id == chat.id)
            for chat in chats
        ]

    def load_chats(self) -> list[ChatData]:
        all_chats = ChatsManager.all_chats()
        return all_chats

    def create_chat(self, chat_data: ChatData) -> None:
        new_chat_list_item = ChatListItem(chat_data, is_open=True)
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
