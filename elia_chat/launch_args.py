from pydantic import BaseModel


class QuickLaunchArgs(BaseModel):
    launch_prompt: str
    launch_prompt_model_name: str
