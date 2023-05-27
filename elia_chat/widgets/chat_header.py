from __future__ import annotations

from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class ChatHeader(Widget):
    title = reactive("Untitled Chat", init=False)
    model_name = reactive("", init=False)

    def watch_model_name(self, new_model_name: str | None) -> None:
        if new_model_name is not None:
            model_static = self.query_one("#model-static", Static)
            model_static.update(new_model_name)

    def watch_title(self, new_title: str | None) -> None:
        if new_title is not None:
            title_static = self.query_one("#title-static", Static)
            title_static.update(new_title)

    def compose(self) -> ComposeResult:
        yield Static(self.title, id="title-static")
        yield Static(self.model_name, id="model-static")
