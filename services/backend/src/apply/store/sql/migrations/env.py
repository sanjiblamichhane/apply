import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from apply.store.sql.models import Base

config = context.config
url = config.get_main_option("sqlalchemy.url")
if not url:
    from apply.settings import AppSettings

    url = AppSettings().database_url


def _configure(connection=None) -> None:
    context.configure(
        connection=connection,
        url=None if connection is not None else url,
        target_metadata=Base.metadata,
        compare_type=True,
        compare_server_default=False,
    )


def _run(connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    _configure()
    with context.begin_transaction():
        context.run_migrations()
else:
    existing = config.attributes.get("connection")
    if existing is not None:
        _run(existing)
    else:
        asyncio.run(_online())
