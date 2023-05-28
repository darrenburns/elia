from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, func, JSON, desc
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship


class MessageDao(SQLModel, table=True):
    __tablename__ = "message"

    id: int = Field(default=None, primary_key=True)
    chat_id: int | None = Field(foreign_key="chat.id")
    chat: ChatDao = Relationship(back_populates="messages")
    role: str
    content: str
    timestamp: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    status: str | None
    end_turn: bool | None
    weight: float | None
    meta: dict = Field(sa_column=Column(JSON), default={})
    recipient: str | None


class ChatDao(SQLModel, table=True):
    __tablename__ = "chat"

    id: int = Field(default=None, primary_key=True)
    model: str | None
    title: str | None
    started_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    messages: list[MessageDao] = Relationship(back_populates="chat")

    @staticmethod
    def all() -> list[ChatDao]:
        with Session(engine) as session:
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
                .order_by(desc(subquery.c.max_timestamp))
                .options(selectinload(ChatDao.messages))
            )
            results = session.exec(statement)
            return list(results)

    @staticmethod
    def from_id(chat_id: str) -> ChatDao:
        with Session(engine) as session:
            statement = (
                select(ChatDao)
                .where(ChatDao.id == int(chat_id))
                .options(selectinload(ChatDao.messages))
            )
            result = session.exec(statement).one()
            return result


sqlite_file_name = "elia.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)
