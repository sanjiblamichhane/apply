"""Running the migrations from code: `apply migrate`, start-up checks and the tests all use these."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine

MIGRATIONS = Path(__file__).parent / "migrations"


def alembic_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url)
    return config


def migrate(url: str, revision: str = "head") -> None:
    """Upgrade to ``revision``. Synchronous (alembic's env runs its own loop); call it outside a running loop."""
    command.upgrade(alembic_config(url), revision)


def downgrade(url: str, revision: str = "base") -> None:
    command.downgrade(alembic_config(url), revision)


def head() -> str:
    return ScriptDirectory.from_config(alembic_config("postgresql+asyncpg://unused/unused")).get_current_head() or ""


async def current(url: str) -> str | None:
    """The database's revision (None: never migrated or unreachable tables)."""
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(lambda c: MigrationContext.configure(c).get_current_revision())
    finally:
        await engine.dispose()


def is_current(url: str) -> bool:
    return asyncio.run(current(url)) == head()
