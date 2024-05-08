from __future__ import annotations

from dataclasses import dataclass
import datetime

from textual import log

from elia_chat.database.converters import (
    chat_dao_to_chat_data,
    chat_message_to_message_dao,
    message_dao_to_chat_message,
)
from elia_chat.database.database import get_session
from elia_chat.database.models import ChatDao, MessageDao
from elia_chat.models import ChatData, ChatMessage


@dataclass
class ChatsManager:
    @staticmethod
    async def all_chats() -> list[ChatData]:
        chat_daos = await ChatDao.all()
        return [chat_dao_to_chat_data(chat) for chat in chat_daos]

    @staticmethod
    async def get_chat(chat_id: int) -> ChatData:
        chat_dao = await ChatDao.from_id(chat_id)
        return chat_dao_to_chat_data(chat_dao)

    @staticmethod
    async def get_messages(
        chat_id: int,
    ) -> list[ChatMessage]:
        async with get_session() as session:
            try:
                chat: ChatDao | None = await session.get(ChatDao, chat_id)
            except ValueError:
                raise RuntimeError(
                    f"Malformed chat ID {chat_id!r}. "
                    f"I couldn't convert it to an integer."
                )

            if not chat:
                raise RuntimeError(f"Chat with ID {chat_id} not found.")
            message_daos = chat.messages
            await session.commit()

        # Convert MessageDao objects to ChatMessages
        model = chat.model
        chat_messages: list[ChatMessage] = []
        for message_dao in message_daos:
            chat_message = message_dao_to_chat_message(message_dao, model)
            chat_messages.append(chat_message)

        log.debug(f"Retrieved {len(chat_messages)} chats for chat {chat_id!r}")
        return chat_messages

    @staticmethod
    async def create_chat(chat_data: ChatData) -> int:
        log.debug(f"Creating chat in database: {chat_data!r}")

        model = chat_data.model
        lookup_key = model.lookup_key
        async with get_session() as session:
            chat = ChatDao(
                model=lookup_key,
                title="",
                started_at=datetime.datetime.now(datetime.UTC),
            )
            session.add(chat)
            await session.commit()

            chat_id = chat.id
            for message in chat_data.messages:
                litellm_message = message.message
                content = litellm_message["content"]
                new_message = MessageDao(
                    chat_id=chat_id,
                    role=litellm_message["role"],
                    content=content if isinstance(content, str) else "",
                    model=lookup_key,
                    timestamp=message.timestamp,
                )
                (await chat.awaitable_attrs.messages).append(new_message)

            await session.commit()

        return chat.id

    @staticmethod
    async def add_message_to_chat(chat_id: int, message: ChatMessage) -> None:
        async with get_session() as session:
            chat: ChatDao | None = await session.get(ChatDao, chat_id)
            if not chat:
                raise Exception(f"Chat with ID {chat_id} not found.")
            message_dao = chat_message_to_message_dao(message, chat_id)
            (await chat.awaitable_attrs.messages).append(message_dao)
            session.add(chat)
            await session.commit()
