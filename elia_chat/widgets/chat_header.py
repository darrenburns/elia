from __future__ import annotations
from dataclasses import dataclass

from rich.console import ConsoleRenderable, RichCast
from rich.markup import escape

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatData
from elia_chat.screens.rename_chat_screen import RenameChat


class TitleStatic(Static):
    @dataclass
    class ChatRenamed(Message):
        chat_id: int
        new_title: str

    def __init__(
        self,
        chat_id: int,
        renderable: ConsoleRenderable | RichCast | str = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.chat_id = chat_id

    def begin_rename(self) -> None:
        self.app.push_screen(RenameChat(), callback=self.request_chat_rename)

    def action_rename_chat(self) -> None:
        self.begin_rename()

    async def request_chat_rename(self, new_title: str) -> None:
        self.post_message(self.ChatRenamed(self.chat_id, new_title))


class ChatHeader(Widget):
    def __init__(
        self,
        chat: ChatData,
        model: EliaChatModel,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.chat = chat
        self.model = model

    def update_header(self, chat: ChatData, model: EliaChatModel):
        self.chat = chat
        self.model = model

        model_static = self.query_one("#model-static", Static)
        title_static = self.query_one("#title-static", Static)

        model_static.update(self.model_static_content())
        title_static.update(self.title_static_content())

    def title_static_content(self) -> str:
        chat = self.chat
        content = escape(chat.title or chat.short_preview) if chat else "Empty chat"
        return f"[@click=rename_chat]{content}[/]"

    def model_static_content(self) -> str:
        model = self.model
        return escape(model.display_name or model.name) if model else "Unknown model"

    def compose(self) -> ComposeResult:
        yield TitleStatic(self.chat.id, self.title_static_content(), id="title-static")
        yield Static(self.model_static_content(), id="model-static")
