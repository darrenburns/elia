from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.llms.base import LLM

callback = AsyncIteratorCallbackHandler()


@dataclass
class GPTModel:
    name: str
    icon: str
    provider: str
    product: str
    description: str
    css_class: str
    model: BaseChatModel | LLM
    token_limit: int


DEFAULT_MODEL = GPTModel(
    name="gpt-3.5-turbo",
    icon="⚡️",
    provider="OpenAI",
    product="ChatGPT",
    description="The fastest ChatGPT model, great for most everyday tasks.",
    css_class="gpt35",
    model=ChatOpenAI(
        model="gpt-3.5-turbo",
        streaming=True,
        callbacks=[callback],
    ),
    token_limit=16385,
)
AVAILABLE_MODELS = [
    DEFAULT_MODEL,
    GPTModel(
        name="gpt-4-turbo",
        icon="🧠",
        provider="OpenAI",
        product="ChatGPT",
        description="The most powerful ChatGPT model, capable of "
        "complex tasks which require advanced reasoning.",
        css_class="gpt4",
        model=ChatOpenAI(
            model="gpt-4-turbo",
            streaming=True,
            callbacks=[callback],
        ),
        token_limit=128000,
    ),
]
MODEL_MAPPING: Dict[str, GPTModel] = {model.name: model for model in AVAILABLE_MODELS}


def get_model_by_name(model_name: str) -> GPTModel:
    """Given the name of a model as a string, return the GPTModel."""
    return MODEL_MAPPING[model_name]
