from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session

from elia_chat.database.converters import (
    chat_dao_to_chat_data,
    chat_message_to_message_dao,
)
from elia_chat.database.models import ChatDao, MessageDao, engine
from elia_chat.models import ChatData, ChatMessage


@dataclass
class ChatsManager:
    @staticmethod
    def all_chats() -> list[ChatData]:
        chat_daos = ChatDao.all()
        return [chat_dao_to_chat_data(chat) for chat in chat_daos]

    @staticmethod
    def create_chat(chat_data: ChatData) -> int:
        chat = ChatDao(model=chat_data.model_name, title="Untitled chat")

        for message in chat_data.messages:
            new_message = MessageDao(
                role=message.get("role"), content=message.get("content")
            )
            chat.messages.append(new_message)

        with Session(engine) as session:
            session.add(chat)
            session.commit()
            session.refresh(chat)

        return chat.id

    @staticmethod
    def add_message_to_chat(chat_id: str, message: ChatMessage) -> None:
        with Session(engine) as session:
            chat: ChatDao | None = session.get(ChatDao, chat_id)
            if not chat:
                raise Exception(f"Chat with ID {chat_id} not found.")
            message_dao = chat_message_to_message_dao(message)
            chat.messages.append(message_dao)
            session.add(chat)
            session.commit()
