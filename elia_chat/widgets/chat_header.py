from __future__ import annotations

from rich.markup import escape

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from elia_chat.chats_manager import ChatsManager
from elia_chat.config import EliaChatModel
from elia_chat.models import ChatData
from elia_chat.screens.rename_chat_screen import RenameChat


class TitleStatic(Static):
    def action_rename_chat(self) -> None:
        self.app.push_screen(RenameChat(), callback=self.set_chat_title)

    async def set_chat_title(self, new_title: str) -> None:
        await ChatsManager.rename_chat(self.chat.id, new_title)


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
        content = escape(chat.short_preview) if chat else "Empty chat"
        return f"[@click=rename_chat]{content}[/]"

    def model_static_content(self) -> str:
        model = self.model
        return escape(model.display_name or model.name) if model else "Unknown model"

    def compose(self) -> ComposeResult:
        yield TitleStatic(self.title_static_content(), id="title-static")
        yield Static(self.model_static_content(), id="model-static")
