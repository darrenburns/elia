from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from rich.text import Text


class AppHeader(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def compose(self) -> ComposeResult:
        title_style = self.get_component_rich_style("app-title")
        subtitle_style = self.get_component_rich_style("app-subtitle")
        with Vertical(id="cl-header-container"):
            yield Label(Text("elia", style=title_style))
            yield Label(
                Text(
                    "ChatGPT in the terminal",
                    style=subtitle_style,
                )
            )