import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from elia_chat.database import import_chatgpt
from elia_chat.database.models import MessageDao


@pytest.mark.parametrize(
    "content, expected",
    [
        ({"parts": []}, ""),
        (
            {"parts": ["First paragraph", "Second paragraph"]},
            "First paragraph\nSecond paragraph",
        ),
        ({"parts": ["Only paragraph"]}, "Only paragraph"),
        ({}, ""),
    ],
)
def test_import_preserves_message_parts(tmp_path, monkeypatch, content, expected):
    export = tmp_path / "conversations.json"
    export.write_text(
        json.dumps(
            [
                {
                    "title": "Imported chat",
                    "mapping": {
                        "message": {
                            "message": {
                                "author": {"role": "user"},
                                "content": content,
                            }
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")
        sessions = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        @asynccontextmanager
        async def get_session():
            async with sessions() as session:
                yield session

        monkeypatch.setattr(import_chatgpt, "get_session", get_session)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)

            await import_chatgpt.import_chatgpt_data(export)

            async with sessions() as session:
                message = (await session.exec(select(MessageDao))).one()
                assert message.content == expected
        finally:
            await engine.dispose()

    asyncio.run(scenario())
