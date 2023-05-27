from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


class ChatMessage(TypedDict):
    id: str | None
    role: str
    content: str
    timestamp: float
    status: str | None
    end_turn: bool | None
    weight: float | None
    metadata: dict | None
    recipient: str | None


@dataclass
class ChatData:
    id: str | None
    model_name: str | None
    title: str | None
    create_timestamp: float | None
    messages: list[ChatMessage]

    @property
    def short_preview(self) -> str:
        first_user_message = self.first_user_message
        return first_user_message.get("content", "")[:24] + "..."

    @property
    def first_user_message(self) -> ChatMessage:
        return self.messages[1]

    @property
    def non_system_messages(self) -> list[ChatMessage]:
        return self.messages[1:]

    @property
    def create_time(self) -> datetime:
        return datetime.fromtimestamp(self.create_timestamp or 0)

    @property
    def update_time(self) -> datetime:
        return datetime.fromtimestamp(
            self.messages[-1].get("timestamp", 0) if self.messages else 0
        )
