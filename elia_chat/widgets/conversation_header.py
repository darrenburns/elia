from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static, LoadingIndicator

from elia_chat.widgets.conversation_options import GPTModel


class ConversationHeader(Widget):
    def __init__(
        self,
        title: str,
        generate_title: bool = False,
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
        if title is None and generate_title:
            raise NotImplementedError("Chat name generation not yet implemented.")

        self.title = title
        self.generate_title = generate_title
        self.model_name = ""

    def update_model(self, new_model: GPTModel) -> None:
        self.model_name = new_model.name
        model_static = self.query_one("#model-static", Static)
        model_static.update(new_model.name)
        model_static.remove_class("gpt35-text", "gpt4-text")
        model_static.add_class(f"{new_model.css_class}-text")

    def compose(self) -> ComposeResult:
        yield Static(self.title, id="title-static")
        yield Static(self.model_name, id="model-static")
