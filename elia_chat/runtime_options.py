from pydantic import BaseModel


class RuntimeOptions(BaseModel):
    current_model: str | None = None
    system_prompt: str | None = None
