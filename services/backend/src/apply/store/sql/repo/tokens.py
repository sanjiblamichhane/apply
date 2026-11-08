"""Personal API tokens."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, NotFound

from ..models import ApiToken, User


async def by_hash(session: AsyncSession, token_hash: str) -> tuple[ApiToken, User] | None:
    row = (
        await session.execute(
            select(ApiToken, User).join(User, User.id == ApiToken.owner_id).where(ApiToken.token_hash == token_hash)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def list_(session: AsyncSession, owner_id: str) -> Sequence[ApiToken]:
    return (
        (await session.execute(select(ApiToken).where(ApiToken.owner_id == owner_id).order_by(ApiToken.id.desc())))
        .scalars()
        .all()
    )


async def get(session: AsyncSession, owner_id: str, token_id: str) -> ApiToken:
    row = (
        await session.execute(select(ApiToken).where(ApiToken.owner_id == owner_id, ApiToken.id == token_id))
    ).scalar_one_or_none()
    if row is None:
        raise NotFound(ErrorCode.TOKEN_NOT_FOUND, "No such token")
    return row


async def touch(session: AsyncSession, token_id: str, when: datetime) -> None:
    await session.execute(update(ApiToken).where(ApiToken.id == token_id).values(last_used_at=when))
