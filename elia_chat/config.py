import os
from pydantic import BaseModel, ConfigDict, Field


class OpenAI(BaseModel):
    """Configuration relating to the OpenAI platform."""

    model_config = ConfigDict(frozen=True)

    organization: str | None = Field(default=os.getenv("OPENAI_ORGANIZATION"))
    project: str | None = Field(default=os.getenv("OPENAI_PROJECT"))


class LaunchConfig(BaseModel):
    """The config of the application at launch.

    Values may be sourced via command line options, env vars, config files.
    """

    model_config = ConfigDict(frozen=True)

    # TODO - load from config+cli args+envvars too
    default_model: str = Field(default="gpt-3.5-turbo")
    system_prompt: str = Field(
        default=os.getenv("ELIA_DIRECTIVE", "You are a helpful assistant named Elia.")
    )
    open_ai: OpenAI = Field(default_factory=OpenAI)
