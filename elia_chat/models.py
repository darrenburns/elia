from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from langchain_core.messages import BaseMessage

from elia_chat.config import LaunchConfig, EliaChatModel


def get_available_models(config: LaunchConfig) -> list[EliaChatModel]:
    openai = config.openai
    anthropic = config.anthropic
    return [
        *openai.models,
        *openai.extra_models,
        *anthropic.models,
        *anthropic.extra_models,
    ]


def get_model_by_name(model_name: str, config: LaunchConfig) -> EliaChatModel:
    """Given the name of a model as a string, return the EliaChatModel."""
    available_models = get_available_models(config)
    name_mapping = {model.name: model for model in available_models}
    return name_mapping[model_name]


@dataclass
class ChatData:
    id: str | None
    model_name: str
    title: str | None
    create_timestamp: datetime | None
    messages: list[BaseMessage]

    @property
    def short_preview(self) -> str:
        first_user_message = self.first_user_message
        if first_user_message is None:
            return "Empty chat..."
        first_content = first_user_message.content or ""
        return first_content[:80] + "..."

    @property
    def first_user_message(self) -> BaseMessage | None:
        return self.messages[1] if len(self.messages) > 1 else None

    @property
    def non_system_messages(self) -> list[BaseMessage]:
        return self.messages[1:]

    @property
    def create_time(self) -> datetime:
        return (
            datetime.fromtimestamp(self.create_timestamp or 0)
            .astimezone()
            .replace(tzinfo=UTC)
        )

    @property
    def update_time(self) -> datetime:
        if self.messages:
            message_timestamp = self.messages[-1].additional_kwargs.get("timestamp")

        return message_timestamp.astimezone().replace(tzinfo=UTC)
