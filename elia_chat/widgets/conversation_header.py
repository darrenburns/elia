from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class ConversationHeader(Widget):
    def __init__(
        self,
        title: str | None,
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
            raise NotImplemented("Chat name generation not yet implemented.")

        self.title = title
        self.generate_title = generate_title

    def compose(self) -> ComposeResult:
        yield Static(Text(self.title, style="b"), id="title-static")
        yield Static("gpt-3.5-turbo", id="model-static")  # TODO: Provide means of updating
