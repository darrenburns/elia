from pydantic import BaseModel, ConfigDict


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_model: str
    system_prompt: str
