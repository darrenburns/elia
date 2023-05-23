from dataclasses import dataclass

from rich.console import RenderResult, Console, ConsoleOptions
from rich.padding import Padding
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, OptionList, Static


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
        ), pad=(0, 1))


class ConversationList(Widget):

    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def compose(self) -> ComposeResult:
        with Vertical(id="cl-header-container"):
            yield Static(Text("elia", style=self.get_component_rich_style("app-title")))
            yield Static(Text("ChatGPT in the terminal", style=self.get_component_rich_style("app-subtitle")))

        yield OptionList(
            SavedChat("Osaka", "Tell me about Osaka..."),
            SavedChat("Tokyo", "Tell me about Tokyo..."),
            SavedChat("Okayama", "Tell me about Okayama..."),
            id="cl-option-list"
        )

        with Horizontal(id="cl-button-container"):
            yield Button("[Ctrl+N] New Chat", id="cl-new-chat-button")

    def on_focus(self) -> None:
        print("Sidebar focused")
        self.query_one("#cl-option-list", OptionList).focus()
