from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from langchain.schema import BaseMessage
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.chat_models.base import BaseChatModel

from elia_chat.config import LaunchConfig

callback = AsyncIteratorCallbackHandler()


@dataclass
class GPTModel:
    name: str
    provider: str
    product: str
    description: str
    context_window: int

    def get_langchain_chat_model(
        self,
        launch_config: LaunchConfig,
    ) -> BaseChatModel:
        return ChatOpenAI(
            model=self.name,
            organization=launch_config.open_ai.organization,
            streaming=True,
            callbacks=[callback],
        )


DEFAULT_MODEL = GPTModel(
    name="gpt-3.5-turbo",
    provider="OpenAI",
    product="ChatGPT",
    description="The fastest ChatGPT model, great for most everyday tasks.",
    context_window=16385,
)
AVAILABLE_MODELS = [
    DEFAULT_MODEL,
    GPTModel(
        name="gpt-4-turbo",
        provider="OpenAI",
        product="ChatGPT",
        description="The most powerful ChatGPT model, capable of "
        "complex tasks which require advanced reasoning.",
        context_window=128000,
    ),
]
MODEL_MAPPING: dict[str, GPTModel] = {model.name: model for model in AVAILABLE_MODELS}


def get_model_by_name(model_name: str) -> GPTModel:
    """Given the name of a model as a string, return the GPTModel."""
    return MODEL_MAPPING[model_name]


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
        return (
            datetime.fromtimestamp(
                self.messages[-1].additional_kwargs.get("timestamp", 0)
                if self.messages
                else 0
            )
            .astimezone()
            .replace(tzinfo=UTC)
        )
