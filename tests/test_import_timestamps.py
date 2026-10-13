import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from elia_chat.database import import_chatgpt
from elia_chat.database.models import ChatDao, MessageDao


@pytest.mark.parametrize("timestamp", [1725969600, 0, None])
def test_import_stores_utc_timestamps(tmp_path, monkeypatch, timestamp):
    export = tmp_path / "conversations.json"
    export.write_text(
        json.dumps(
            [
                {
                    "title": "Imported chat",
                    "create_time": timestamp,
                    "mapping": {
                        "message": {
                            "message": {
                                "author": {"role": "user"},
                                "content": {"parts": ["Hello"]},
                                "create_time": timestamp,
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
                chat = (await session.exec(select(ChatDao))).one()
                message = (await session.exec(select(MessageDao))).one()
                expected = datetime.fromtimestamp(timestamp or 0, UTC).replace(
                    tzinfo=None
                )
                assert chat.started_at == expected
                assert message.timestamp == expected
        finally:
            await engine.dispose()

    asyncio.run(scenario())
