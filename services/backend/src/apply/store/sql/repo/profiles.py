"""Profiles: who is applying."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode

from ..models import Profile
from . import get_owned, page


async def get(session: AsyncSession, owner_id: str, profile_id: str, *, for_update: bool = False) -> Profile:
    return await get_owned(session, Profile, owner_id, profile_id, ErrorCode.PROFILE_NOT_FOUND, for_update=for_update)


async def get_any_owner(session: AsyncSession, profile_id: str, *, for_update: bool = False) -> Profile | None:
    """For the worker, which acts for whoever owns the row (its job carries the owner too)."""
    stmt = select(Profile).where(Profile.id == profile_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, after: str | None, limit: int
) -> tuple[Sequence[Profile], str | None]:
    stmt = select(Profile).where(Profile.owner_id == owner_id)
    if pack:
        stmt = stmt.where(Profile.pack == pack)
    return await page(session, stmt, Profile, after=after, limit=limit)


async def count(session: AsyncSession, owner_id: str, pack: str) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(Profile).where(Profile.owner_id == owner_id, Profile.pack == pack)
        )
    ).scalar_one()


async def default_for(session: AsyncSession, owner_id: str, pack: str) -> Profile | None:
    return (
        await session.execute(
            select(Profile).where(Profile.owner_id == owner_id, Profile.pack == pack, Profile.is_default.is_(True))
        )
    ).scalar_one_or_none()


async def clear_default(session: AsyncSession, owner_id: str, pack: str) -> None:
    await session.execute(
        update(Profile)
        .where(Profile.owner_id == owner_id, Profile.pack == pack, Profile.is_default.is_(True))
        .values(is_default=False)
    )


async def newest_other(session: AsyncSession, owner_id: str, pack: str, not_id: str) -> Profile | None:
    return (
        await session.execute(
            select(Profile)
            .where(Profile.owner_id == owner_id, Profile.pack == pack, Profile.id != not_id)
            .order_by(Profile.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def add(session: AsyncSession, **values: Any) -> Profile:
    row = Profile(**values)
    session.add(row)
    await session.flush()
    return row
