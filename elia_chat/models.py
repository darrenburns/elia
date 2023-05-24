from dataclasses import dataclass
from typing import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass
class ChatData:
    # TODO: Fill out some more of the data in here,
    #  then make converters to convert from this to peewee models.
    model_name: str
    messages: list[ChatMessage]

    @property
    def short_preview(self) -> str:
        first_user_message = self.messages[1]
        return first_user_message.get("content", "")[:24] + "..."
