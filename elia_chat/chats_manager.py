from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from textual import log

from elia_chat.database.converters import (
    chat_dao_to_chat_data,
    chat_message_to_message_dao,
    message_dao_to_chat_message,
)
from elia_chat.database.database import get_session
from elia_chat.database.models import ChatDao, MessageDao
from elia_chat.models import ChatData


@dataclass
class ChatsManager:
    @staticmethod
    async def all_chats() -> list[ChatData]:
        chat_daos = await ChatDao.all()
        return [chat_dao_to_chat_data(chat) for chat in chat_daos]

    @staticmethod
    async def get_chat(chat_id: str) -> ChatData:
        chat_dao = await ChatDao.from_id(chat_id)
        return chat_dao_to_chat_data(chat_dao)

    @staticmethod
    async def get_messages(chat_id: str | int) -> list[BaseMessage]:
        async with get_session() as session:
            try:
                chat: ChatDao | None = await session.get(ChatDao, int(chat_id))
            except ValueError:
                raise RuntimeError(
                    f"Malformed chat ID {chat_id!r}. "
                    f"I couldn't convert it to an integer."
                )

            if not chat:
                raise RuntimeError(f"Chat with ID {chat_id} not found.")
            message_daos = chat.messages
            await session.commit()

        # Convert MessageDao objects to BaseMessages
        chat_messages: list[BaseMessage] = []
        for message_dao in message_daos:
            chat_message = message_dao_to_chat_message(message_dao)
            chat_messages.append(chat_message)

        log.debug(f"Retrieved {len(chat_messages)} chats for chat {chat_id!r}")
        return chat_messages

    @staticmethod
    async def create_chat(chat_data: ChatData) -> int:
        log.debug(f"Creating chat in database: {chat_data!r}")

        chat = ChatDao(model=chat_data.model_name, title="Untitled chat")

        for message in chat_data.messages:
            new_message = MessageDao(role=message.type, content=message.content)
            chat.messages.append(new_message)

        async with get_session() as session:
            session.add(chat)
            await session.commit()
            await session.refresh(chat)

        return chat.id

    @staticmethod
    async def add_message_to_chat(chat_id: str, message: BaseMessage) -> None:
        async with get_session() as session:
            chat: ChatDao | None = await session.get(ChatDao, chat_id)
            if not chat:
                raise Exception(f"Chat with ID {chat_id} not found.")
            message_dao = chat_message_to_message_dao(message)
            (await chat.awaitable_attrs.messages).append(message_dao)
            session.add(chat)
            await session.commit()
