from dataclasses import dataclass, field

from elia_chat.models import DEFAULT_MODEL, MODEL_MAPPING, GPTModel


@dataclass
class EliaContext:
    """
    Context that may be passed into Elia on startup.

    For example, if a prompt is submitted during launch.
    """

    chat_message: str | None = field(default=None)
    model_name: str = field(default=DEFAULT_MODEL.name)

    @property
    def gpt_model(self) -> GPTModel:
        gpt_model = MODEL_MAPPING.get(self.model_name)
        if gpt_model is None:
            raise ValueError(f"Unknown model name: {self.model_name}")
        return gpt_model
