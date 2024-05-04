from __future__ import annotations

from rich.markup import escape

from textual.reactive import Reactive, reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatData


class ChatHeader(Widget):
    chat: Reactive[ChatData | None] = reactive(None, init=False, recompose=True)
    model: Reactive[EliaChatModel | None] = reactive(None, init=False, recompose=True)

    def update_header(self):
        model = self.model
        if model is not None:
            model_static = self.query_one("#model-static", Static)
            model_static.update()

        chat = self.chat
        if chat is not None:
            title_static = self.query_one("#title-static", Static)
            title_static.update()

    def compose(self) -> ComposeResult:
        model = self.model
        model_name = (
            escape(model.display_name or model.name) if model else "Unknown model"
        )
        chat = self.chat
        header = escape(chat.short_preview) if chat else "Empty chat"
        yield Static(header, id="title-static")
        yield Static(model_name, id="model-static")
