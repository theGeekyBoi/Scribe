from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker | None = None


def create_sessionmaker(database_path: str) -> async_sessionmaker:
    global _engine, _sessionmaker
    if _sessionmaker is not None:
        return _sessionmaker
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+aiosqlite:///{database_path}"
    _engine = create_async_engine(url, future=True, echo=False)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def init_db(session_maker: async_sessionmaker) -> None:
    from . import models  # noqa: F401

    async with session_maker() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)


async def get_session():
    if _sessionmaker is None:
        raise RuntimeError("Sessionmaker has not been initialized.")
    async with _sessionmaker() as session:  # type: ignore[misc]
        yield session
