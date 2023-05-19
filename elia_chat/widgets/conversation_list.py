from dataclasses import dataclass

from rich.console import RenderResult, Console, ConsoleOptions
from rich.padding import Padding
from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, OptionList


@dataclass
class SavedChat:
    title: str
    subtitle: str

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        yield Padding(Text.assemble(
            (self.title, "b"),
            "\n",
            (self.subtitle, "dim"),
        ), pad=(1, 2))


class ConversationList(Widget):

    def compose(self) -> ComposeResult:
        yield Button("New Chat!", id="new-chat-button")
        yield OptionList(
            SavedChat("Osaka", "Tell me about Osaka..."),
            SavedChat("Tokyo", "Tell me about Tokyo..."),
            SavedChat("Okayama", "Tell me about Okayama..."),
            id="chat-list-option-list"
        )

    def on_focus(self) -> None:
        print("Sidebar focused")
        self.query_one("#chat-list-option-list", OptionList).focus()
