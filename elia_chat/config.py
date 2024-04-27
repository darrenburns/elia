import os
from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import AsyncCallbackHandler

callback = AsyncCallbackHandler()


class EliaChatModel(BaseModel):
    name: str
    provider: Literal["openai", "anthropic"]
    description: str = Field("A chat model")
    product: str = Field("")
    context_window: int = Field(default=16_000)
    temperature: int = Field(default=1.0)

    def get_langchain_chat_model(
        self,
        launch_config: "LaunchConfig",
    ) -> BaseChatModel:
        match self.provider:
            case "openai":
                return ChatOpenAI(
                    model=self.name,
                    organization=launch_config.openai.organization,
                    streaming=True,
                    callbacks=[callback],
                    temperature=self.temperature,
                )
            case "anthropic":
                return ChatAnthropic(
                    model_name=self.name,
                    callbacks=[callback],
                    timeout=None,
                    api_key=launch_config.anthropic.api_key,  # type: ignore
                    temperature=self.temperature,
                )


def get_default_openai_models() -> list[EliaChatModel]:
    return [
        EliaChatModel(
            name="gpt-3.5-turbo",
            provider="openai",
            product="ChatGPT",
            description="The fastest ChatGPT model, great for most everyday tasks",
            context_window=16_385,
        ),
        EliaChatModel(
            name="gpt-4-turbo",
            provider="openai",
            product="ChatGPT",
            description="The most powerful ChatGPT model, capable of "
            "complex tasks which require advanced reasoning",
            context_window=128_000,
        ),
    ]


def get_default_anthropic_models() -> list[EliaChatModel]:
    return [
        EliaChatModel(
            name="claude-3-haiku-20240307",
            provider="anthropic",
            product="Claude 3",
            description=(
                "Fastest and most compact model for near-instant responsiveness"
            ),
            context_window=200_000,
        ),
        EliaChatModel(
            name="claude-3-sonnet-20240229",
            provider="anthropic",
            product="Claude 3",
            description=(
                "Ideal balance of intelligence and speed for enterprise workloads"
            ),
            context_window=200_000,
        ),
        EliaChatModel(
            name="claude-3-opus-20240229",
            provider="anthropic",
            product="Claude 3",
            description="Most powerful model for highly complex tasks",
            context_window=200_000,
        ),
    ]


class OpenAI(BaseModel):
    """Configuration relating to the OpenAI platform."""

    model_config = ConfigDict(frozen=True)

    api_key: SecretStr | None = Field(default=os.getenv("OPENAI_API_KEY"))
    organization: str | None = Field(default=os.getenv("OPENAI_ORGANIZATION"))
    models: list[EliaChatModel] = Field(default_factory=get_default_openai_models)
    extra_models: list[EliaChatModel] = Field(default_factory=list)
    # project: str | None = Field(default=os.getenv("OPENAI_PROJECT"))


class Anthropic(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: SecretStr | None = Field(default=os.getenv("ANTHROPIC_API_KEY"))
    models: list[EliaChatModel] = Field(default_factory=get_default_anthropic_models)
    extra_models: list[EliaChatModel] = Field(default_factory=list)


class LaunchConfig(BaseModel):
    """The config of the application at launch.

    Values may be sourced via command line options, env vars, config files.
    """

    model_config = ConfigDict(frozen=True)

    # TODO - load from config+cli args+envvars too
    default_model: str = Field(default="gpt-3.5-turbo")
    system_prompt: str = Field(
        default=os.getenv(
            "ELIA_SYSTEM_PROMPT", "You are a helpful assistant named Elia."
        )
    )
    openai: OpenAI = Field(default_factory=OpenAI)
    anthropic: Anthropic = Field(default_factory=Anthropic)
