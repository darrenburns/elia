from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, func, JSON
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
            statement = select(ChatDao).options(selectinload(ChatDao.messages))
            results = session.exec(statement)
            return list(results)


sqlite_file_name = "elia.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)
