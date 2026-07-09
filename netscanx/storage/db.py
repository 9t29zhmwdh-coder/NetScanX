from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from netscanx.storage.paths import resolve_db_path
from netscanx.storage.schema import Base

_engines: dict[str, AsyncEngine] = {}


def get_engine(db_path: Path | None = None) -> AsyncEngine:
    """Lazily creates (and caches, keyed by resolved path) the async engine
    for the given DB path, or the default resolved path if omitted."""
    resolved = db_path if db_path is not None else resolve_db_path()
    key = str(resolved)
    engine = _engines.get(key)
    if engine is None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{resolved}")

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        _engines[key] = engine
    return engine


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
