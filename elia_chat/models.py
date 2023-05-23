from dataclasses import dataclass
from typing import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass
class Conversation:
    # TODO: Fill out some more of the data in here,
    #  then make converters to convert from this to peewee models.
    messages: list[ChatMessage]
