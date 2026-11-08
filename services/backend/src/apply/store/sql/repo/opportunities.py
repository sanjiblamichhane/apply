"""Opportunities: what is apply for."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode

from ..models import Opportunity
from . import get_owned, page


async def get(session: AsyncSession, owner_id: str, opportunity_id: str, *, for_update: bool = False) -> Opportunity:
    return await get_owned(
        session, Opportunity, owner_id, opportunity_id, ErrorCode.OPPORTUNITY_NOT_FOUND, for_update=for_update
    )


async def get_any_owner(session: AsyncSession, opportunity_id: str, *, for_update: bool = False) -> Opportunity | None:
    """For the worker, which acts for whoever owns the row (its job carries the owner too)."""
    stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def by_ref(session: AsyncSession, owner_id: str, external_ref: str) -> Opportunity | None:
    return (
        await session.execute(
            select(Opportunity).where(Opportunity.owner_id == owner_id, Opportunity.external_ref == external_ref)
        )
    ).scalar_one_or_none()


async def seen_again(session: AsyncSession, opportunity: Opportunity) -> None:
    opportunity.last_seen_at = datetime.now(UTC)
    await session.flush()


async def insert_new(session: AsyncSession, values: dict[str, Any]) -> str | None:
    """Insert unless the owner already has this external_ref (a paste racing another). Returns the new id or None."""
    stmt = (
        insert(Opportunity)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[Opportunity.owner_id, Opportunity.external_ref])
    )
    return (await session.execute(stmt.returning(Opportunity.id))).scalar_one_or_none()


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, after: str | None, limit: int
) -> tuple[Sequence[Opportunity], str | None]:
    stmt = select(Opportunity).where(Opportunity.owner_id == owner_id)
    if pack:
        stmt = stmt.where(Opportunity.pack == pack)
    return await page(session, stmt, Opportunity, after=after, limit=limit)


async def by_any_url(session: AsyncSession, owner_id: str, urls: list[str]) -> Sequence[Opportunity]:
    """The owner's opportunities known by any of these (canonical) URLs: as listed, as posted, or as the form."""
    if not urls:
        return []
    return (
        (
            await session.execute(
                select(Opportunity)
                .where(
                    Opportunity.owner_id == owner_id,
                    or_(
                        Opportunity.external_ref.in_(urls),
                        Opportunity.source_url.in_(urls),
                        Opportunity.apply_url.in_(urls),
                    ),
                )
                .order_by(Opportunity.id.desc())
            )
        )
        .scalars()
        .all()
    )
