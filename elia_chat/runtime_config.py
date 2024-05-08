from pydantic import BaseModel, ConfigDict

from elia_chat.config import EliaChatModel


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_model: EliaChatModel
    system_prompt: str
