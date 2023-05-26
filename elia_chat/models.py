from __future__ import annotations

from dataclasses import dataclass
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
    create_time: float | None
    messages: list[ChatMessage]

    @property
    def short_preview(self) -> str:
        first_user_message = self.messages[1]
        return first_user_message.get("content", "")[:24] + "..."
