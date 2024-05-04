from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from litellm.types.completion import ChatCompletionMessageParam

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
class ChatMessage:
    message: ChatCompletionMessageParam
    timestamp: datetime | None
    model: str


@dataclass
class ChatData:
    id: int | None  # Can be None before the chat gets assigned ID from database.
    model_name: str
    title: str | None
    create_timestamp: datetime | None
    messages: list[ChatMessage]

    @property
    def short_preview(self) -> str:
        first_message = self.first_user_message.message

        if "content" in first_message:
            first_message = first_message["content"]
            # We have content, but it's not guaranteed to be a string quite yet.
            # In the case of tool calls or image generation requests, we can
            # have non-string types here. We're not handling/considering this atm.
            if first_message and isinstance(first_message, str):
                if len(first_message) > 77:
                    return first_message[:77] + "..."
                else:
                    return first_message

        return ""

    @property
    def first_user_message(self) -> ChatMessage:
        return self.messages[1]

    @property
    def non_system_messages(
        self,
    ) -> list[ChatMessage]:
        return self.messages[1:]

    @property
    def update_time(self) -> datetime:
        message_timestamp = self.messages[-1].timestamp
        return message_timestamp.astimezone().replace(tzinfo=UTC)
