"""The database: one async engine per process, and a transaction helper everything else goes through."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from ulid import ULID


def new_id() -> str:
    """26 characters, time first: ids sort in the order rows were made, which is what list pages page by."""
    return str(ULID())


class Database:
    def __init__(self, url: str, *, pool_size: int = 5):
        self.url = url
        # hide_parameters: a failed statement's error (and so its log line) shows the SQL without the values bound
        # to it, which are people's profiles, postings and documents.
        self.engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=pool_size,
            pool_recycle=1800,
            hide_parameters=True,
        )
        self.sessions = async_sessionmaker(bind=self.engine, expire_on_commit=False)

    @property
    def dsn(self) -> str:
        """The URL as plain asyncpg wants it (for LISTEN)."""
        return make_url(self.url).set(drivername="postgresql").render_as_string(hide_password=False)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """One transaction: commits when the block succeeds, rolls back when it raises."""
        async with self.sessions() as session, session.begin():
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
