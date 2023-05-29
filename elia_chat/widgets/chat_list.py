from dataclasses import dataclass

import humanize
from rich.console import RenderResult, Console, ConsoleOptions
from rich.padding import Padding
from rich.text import Text
from textual import log, on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData


@dataclass
class ChatListItemRenderable:
    chat: ChatData

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        create_time_string = humanize.naturaltime(self.chat.create_time)
        subtitle = f"{create_time_string}"
        yield Padding(
            Text.assemble(
                (self.chat.short_preview, "b"),
                "\n",
                (subtitle, "dim"),
            ),
            pad=(0, 1),
        )


class ChatListItem(Option):
    def __init__(self, chat: ChatData) -> None:
        super().__init__(ChatListItemRenderable(chat))
        self.chat = chat


class ChatList(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    @dataclass
    class ChatOpened(Message):
        chat: ChatData

    def compose(self) -> ComposeResult:
        with Vertical(id="cl-header-container"):
            yield Static(Text("elia", style=self.get_component_rich_style("app-title")))
            yield Static(
                Text(
                    "ChatGPT in the terminal",
                    style=self.get_component_rich_style("app-subtitle"),
                )
            )

        chats = self.load_chats()
        self.options = [ChatListItem(chat) for chat in chats]

        option_list = OptionList(
            *self.options,
            id="cl-option-list",
        )
        yield option_list

        with Horizontal(id="cl-button-container"):
            yield Button("[Ctrl+N] New Chat", id="cl-new-chat-button")

    @on(OptionList.OptionSelected, "#cl-option-list")
    def post_chat_opened(self, event: OptionList.OptionSelected) -> None:
        assert isinstance(event.option, ChatListItem)
        chat = event.option.chat
        self.post_message(ChatList.ChatOpened(chat=chat))

    def on_focus(self) -> None:
        log.debug("Sidebar focused")
        self.query_one("#cl-option-list", OptionList).focus()

    def reload_and_refresh(self) -> None:
        """Reload the chats and refresh the widget. Can be used to
        update the ordering/previews/titles etc contained in the list."""
        chats = self.load_chats()
        self.options = [ChatListItem(chat) for chat in chats]
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        option_list.add_options(self.options)
        option_list.highlighted = 0

    def load_chats(self) -> list[ChatData]:
        all_chats = ChatsManager.all_chats()
        return all_chats

    def create_chat(self, chat_data: ChatData) -> None:
        new_chat_list_item = ChatListItem(chat_data)
        log.debug(f"Creating new chat {new_chat_list_item!r}")

        option_list = self.query_one(OptionList)
        self.options = [
            new_chat_list_item,
            *self.options,
        ]
        option_list.clear_options()
        option_list.add_options(self.options)
        option_list.highlighted = 0
