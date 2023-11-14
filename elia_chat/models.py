from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from langchain.schema import BaseMessage

from elia_chat.widgets.chat_options import GPTModel, MODEL_MAPPING, DEFAULT_MODEL


@dataclass
class ChatData:
    id: str | None
    model_name: str
    title: str | None
    create_timestamp: float | None
    messages: list[BaseMessage]

    @property
    def short_preview(self) -> str:
        first_user_message = self.first_user_message
        if first_user_message is None:
            return "Empty chat..."
        first_content = first_user_message.content or ""
        return first_content[:24] + "..."

    @property
    def first_user_message(self) -> BaseMessage | None:
        return self.messages[1] if len(self.messages) > 1 else None

    @property
    def non_system_messages(self) -> list[BaseMessage]:
        return self.messages[1:]

    @property
    def create_time(self) -> datetime:
        return datetime.fromtimestamp(self.create_timestamp or 0).astimezone()

    @property
    def update_time(self) -> datetime:
        return datetime.fromtimestamp(
            self.messages[-1].get("timestamp", 0) if self.messages else 0
        )


@dataclass
class EliaContext:
    """
    Elia Context
    """

    chat_message: Optional[str] = None
    model_name: str = DEFAULT_MODEL.name

    @property
    def gpt_model(self) -> GPTModel:
        gpt_model = MODEL_MAPPING.get(self.model_name)
        if gpt_model is None:
            raise ValueError(f"Unknown model name: {self.model_name}")
        return gpt_model
