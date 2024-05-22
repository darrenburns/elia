from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, func, JSON, desc
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, SQLModel, select

from elia_chat.database.database import get_session


class SystemPromptsDao(AsyncAttrs, SQLModel, table=True):
    __tablename__ = "system_prompt"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    prompt: str
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(), server_default=func.now())
    )


class MessageDao(AsyncAttrs, SQLModel, table=True):
    __tablename__ = "message"

    id: int | None = Field(default=None, primary_key=True)
    chat_id: Optional[int] = Field(foreign_key="chat.id")
    chat: Optional["ChatDao"] = Relationship(back_populates="messages")
    role: str
    content: str
    timestamp: datetime | None = Field(
        sa_column=Column(DateTime(), server_default=func.now())
    )
    meta: dict[Any, Any] = Field(sa_column=Column(JSON), default={})
    parent_id: Optional[int] = Field(
        foreign_key="message.id", default=None, nullable=True
    )
    parent: Optional["MessageDao"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={"remote_side": "MessageDao.id"},
    )
    """The message this message is responding to."""
    replies: list["MessageDao"] = Relationship(back_populates="parent")
    """The replies to this message
    (could be multiple replies e.g. from different models).
    """
    model: str | None
    """The model that wrote this response. (Could switch models mid-chat, possibly)"""


class ChatDao(AsyncAttrs, SQLModel, table=True):
    __tablename__ = "chat"

    id: int = Field(default=None, primary_key=True)
    model: str
    title: str | None
    started_at: datetime | None = Field(
        sa_column=Column(DateTime(), server_default=func.now())
    )
    messages: list[MessageDao] = Relationship(back_populates="chat")
    archived: bool = Field(default=False)

    @staticmethod
    async def all() -> list["ChatDao"]:
        async with get_session() as session:
            # Create a subquery that finds the maximum
            # (most recent) timestamp for each chat.
            max_timestamp: Any = func.max(MessageDao.timestamp).label("max_timestamp")
            subquery = (
                select(MessageDao.chat_id, max_timestamp)
                .group_by(MessageDao.chat_id)
                .alias("subquery")
            )

            statement = (
                select(ChatDao)
                .join(subquery, subquery.c.chat_id == ChatDao.id)
                .where(ChatDao.archived is False)
                .order_by(desc(subquery.c.max_timestamp))
                .options(selectinload(ChatDao.messages))
            )
            results = await session.exec(statement)
            return list(results)

    @staticmethod
    async def from_id(chat_id: int) -> "ChatDao":
        async with get_session() as session:
            statement = (
                select(ChatDao)
                .where(ChatDao.id == int(chat_id))
                .options(selectinload(ChatDao.messages))
            )
            result = await session.exec(statement)
            return result.one()

    @staticmethod
    async def rename_chat(chat_id: int, new_title: str) -> None:
        async with get_session() as session:
            chat = await ChatDao.from_id(chat_id)
            chat.title = new_title
            print(f"setting chat title to {new_title!r}")
            session.add(chat)
            await session.commit()
