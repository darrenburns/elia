from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label

from rich.text import Text


class AppHeader(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def compose(self) -> ComposeResult:
        title_style = self.get_component_rich_style("app-title")
        subtitle_style = self.get_component_rich_style("app-subtitle")

        with Horizontal():
            with Vertical(id="cl-header-container"):
                yield Label(
                    Text.assemble(
                        ("elia ", title_style + Style(bold=True)),
                        ("///", subtitle_style),
                        (" llm tools", title_style),
                    )
                )
            yield Button("gpt-3.5-turbo")
