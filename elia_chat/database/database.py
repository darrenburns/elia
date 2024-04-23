from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlmodel import SQLModel
from elia_chat.locations import data_directory

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


sqlite_file_name = data_directory() / "elia.sqlite"
sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"
engine = create_async_engine(sqlite_url)


async def create_database():
    async with engine.begin() as conn:
        # TODO - check if exists, use Alembic.
        print(data_directory())
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
