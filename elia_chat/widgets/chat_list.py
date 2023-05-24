from dataclasses import dataclass

from rich.console import RenderResult, Console, ConsoleOptions
from rich.padding import Padding
from rich.text import Text
from textual import log
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, OptionList, Static

from elia_chat.models import ChatData


@dataclass
class SavedChat:
    title: str
    subtitle: str

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Padding(
            Text.assemble(
                (self.title, "b"),
                "\n",
                (self.subtitle, "dim"),
            ),
            pad=(0, 1),
        )


class ChatList(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def compose(self) -> ComposeResult:
        with Vertical(id="cl-header-container"):
            yield Static(Text("elia", style=self.get_component_rich_style("app-title")))
            yield Static(
                Text(
                    "ChatGPT in the terminal",
                    style=self.get_component_rich_style("app-subtitle"),
                )
            )

        self.options = [
            SavedChat("Osaka", "Tell me about Osaka..."),
            SavedChat("Tokyo", "Tell me about Tokyo..."),
            SavedChat("Okayama", "Tell me about Okayama..."),
        ]

        option_list = OptionList(
            *self.options,
            id="cl-option-list",
        )
        yield option_list

        with Horizontal(id="cl-button-container"):
            yield Button("[Ctrl+N] New Chat", id="cl-new-chat-button")

    def on_focus(self) -> None:
        log.debug("Sidebar focused")
        self.query_one("#cl-option-list", OptionList).focus()

    def create_chat(self, chat_data: ChatData) -> None:
        new_chat = SavedChat("Untitled Chat", chat_data.short_preview)
        log.debug(f"Creating new chat {new_chat!r}")

        option_list = self.query_one(OptionList)
        # Update our in-memory idea of what the chats are
        self.options = [
            new_chat,
            *self.options,
        ]
        option_list.clear_options()
        option_list.add_options(self.options)
        option_list.highlighted = 0
