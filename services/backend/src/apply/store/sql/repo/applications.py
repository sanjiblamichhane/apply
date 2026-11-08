"""Applications, and where each is in its pipeline."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apply.errors import ErrorCode

from ..models import Application, Opportunity, StageHistory
from . import get_owned, page

_LOADED = (
    selectinload(Application.opportunity),
    selectinload(Application.stage),
    selectinload(Application.current_documents),
)


async def get(session: AsyncSession, owner_id: str, application_id: str, *, for_update: bool = False) -> Application:
    return await get_owned(
        session, Application, owner_id, application_id, ErrorCode.APPLICATION_NOT_FOUND, for_update=for_update
    )


async def loaded(session: AsyncSession, application: Application) -> Application:
    """The application with its opportunity and stage, as the API shows it."""
    await session.flush()
    await session.refresh(application, attribute_names=["opportunity", "stage", "current_documents"])
    return application


async def get_any_owner(session: AsyncSession, application_id: str, *, for_update: bool = False) -> Application | None:
    stmt = select(Application).where(Application.id == application_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def by_opportunity(session: AsyncSession, owner_id: str, opportunity_id: str) -> Application | None:
    return (
        await session.execute(
            select(Application).where(Application.owner_id == owner_id, Application.opportunity_id == opportunity_id)
        )
    ).scalar_one_or_none()


async def add(session: AsyncSession, **values: Any) -> Application:
    row = Application(**values)
    session.add(row)
    await session.flush()
    return row


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, stage_id: str | None, after: str | None, limit: int
) -> tuple[Sequence[Application], str | None]:
    stmt = select(Application).options(*_LOADED).where(Application.owner_id == owner_id)
    if pack:
        stmt = stmt.join(Opportunity, Opportunity.id == Application.opportunity_id).where(Opportunity.pack == pack)
    if stage_id:
        stmt = stmt.where(Application.stage_id == stage_id)
    return await page(session, stmt, Application, after=after, limit=limit)


async def open_history(session: AsyncSession, application_id: str) -> StageHistory | None:
    return (
        await session.execute(
            select(StageHistory)
            .where(StageHistory.application_id == application_id, StageHistory.exited_at.is_(None))
            .order_by(StageHistory.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def close_history(session: AsyncSession, application_id: str, outcome: str) -> None:
    await session.execute(
        update(StageHistory)
        .where(StageHistory.application_id == application_id, StageHistory.exited_at.is_(None))
        .values(exited_at=func.now(), outcome=outcome)
    )


async def add_history(session: AsyncSession, **values: Any) -> StageHistory:
    row = StageHistory(**values)
    session.add(row)
    await session.flush()
    return row


async def history(session: AsyncSession, owner_id: str, application_id: str) -> Sequence[StageHistory]:
    return (
        (
            await session.execute(
                select(StageHistory)
                .options(selectinload(StageHistory.stage))
                .where(StageHistory.owner_id == owner_id, StageHistory.application_id == application_id)
                .order_by(StageHistory.id.desc())
            )
        )
        .scalars()
        .all()
    )
