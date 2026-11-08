"""
Queries. Every function that reads or writes a row someone owns takes ``owner_id`` and filters on it: there is
no way to ask for another owner's row by id. A row that isn't the caller's is "not found", never "forbidden",
so ids can't be probed.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, NotFound

MAX_PAGE = 200


async def get_owned[T](
    session: AsyncSession, model: type[T], owner_id: str, row_id: str, code: ErrorCode, *, for_update: bool = False
) -> T:
    stmt = select(model).where(model.id == row_id, model.owner_id == owner_id)  # type: ignore[attr-defined]
    if for_update:
        stmt = stmt.with_for_update()
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFound(code, f"No {model.__tablename__} row {row_id} for this owner")  # type: ignore[attr-defined]
    return row


async def page(
    session: AsyncSession, stmt: Select[Any], model: Any, *, after: str | None, limit: int
) -> tuple[Sequence[Any], str | None]:
    """Newest first, ``limit`` at a time; ``after`` is the last id of the page before."""
    limit = max(1, min(limit, MAX_PAGE))
    if after:
        stmt = stmt.where(model.id < after)
    rows = (await session.execute(stmt.order_by(model.id.desc()).limit(limit + 1))).scalars().all()
    more = len(rows) > limit
    rows = rows[:limit]
    return rows, (rows[-1].id if more and rows else None)
