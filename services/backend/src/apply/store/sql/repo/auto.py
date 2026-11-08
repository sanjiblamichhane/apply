"""Auto runs and their screenshots."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apply.errors import ErrorCode

from ..models import Application, AutoRun, AutoScreenshot, Match, Opportunity
from . import get_owned

# Being prepared; "ready" then waits for the person to send it.
ACTIVE = ("starting", "writing")


async def run(session: AsyncSession, owner_id: str, run_id: str, *, for_update: bool = False) -> AutoRun:
    return await get_owned(session, AutoRun, owner_id, run_id, ErrorCode.AUTO_RUN_NOT_FOUND, for_update=for_update)


async def run_any_owner(session: AsyncSession, run_id: str, *, for_update: bool = False) -> AutoRun | None:
    stmt = select(AutoRun).where(AutoRun.id == run_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def for_match(session: AsyncSession, owner_id: str, match_id: str) -> AutoRun | None:
    return (
        await session.execute(select(AutoRun).where(AutoRun.owner_id == owner_id, AutoRun.match_id == match_id))
    ).scalar_one_or_none()


async def runs(session: AsyncSession, owner_id: str, statuses: Sequence[str]) -> Sequence[AutoRun]:
    return (
        (
            await session.execute(
                select(AutoRun)
                .options(selectinload(AutoRun.match).selectinload(Match.opportunity))
                .where(AutoRun.owner_id == owner_id, AutoRun.status.in_(statuses))
                .order_by(AutoRun.id.desc())
                .limit(200)
            )
        )
        .scalars()
        .all()
    )


async def loaded(session: AsyncSession, owner_id: str, run_id: str) -> AutoRun:
    found = (
        await session.execute(
            select(AutoRun)
            .options(selectinload(AutoRun.match).selectinload(Match.opportunity))
            .where(AutoRun.owner_id == owner_id, AutoRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if found is None:
        return await run(session, owner_id, run_id)  # raises not found
    return found


async def counts(session: AsyncSession, owner_id: str) -> dict[str, int]:
    rows = (
        await session.execute(
            select(AutoRun.status, func.count()).where(AutoRun.owner_id == owner_id).group_by(AutoRun.status)
        )
    ).all()
    return {status: n for status, n in rows}


async def ready_since(session: AsyncSession, owner_id: str, since: datetime, *, not_id: str) -> int:
    """Runs prepared since ``since``: what the daily cap counts."""
    return (
        await session.execute(
            select(func.count())
            .select_from(AutoRun)
            .where(
                AutoRun.owner_id == owner_id,
                AutoRun.id != not_id,
                AutoRun.ready_at >= since,
                AutoRun.status.in_(("ready", "sent")),
            )
        )
    ).scalar_one()


async def issuer_activity(
    session: AsyncSession, owner_id: str, *, since: datetime, not_application: str | None
) -> list[tuple[str, str]]:
    """(issuer name, why) for every application sent since ``since``, or prepared by Auto and not sent yet."""
    sent = (
        await session.execute(
            select(Opportunity.issuer_name, Application.id)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .where(Application.owner_id == owner_id, Application.submitted_at >= since)
        )
    ).all()
    busy = (
        await session.execute(
            select(Opportunity.issuer_name, AutoRun.application_id)
            .join(Match, Match.id == AutoRun.match_id)
            .join(Opportunity, Opportunity.id == Match.opportunity_id)
            .where(AutoRun.owner_id == owner_id, AutoRun.status == "ready")
        )
    ).all()
    return [(name, "sent") for name, app in sent if app != not_application] + [
        (name, "auto") for name, app in busy if app != not_application
    ]


async def to_sweep(session: AsyncSession, now: datetime) -> Sequence[AutoRun]:
    return (
        (
            await session.execute(
                select(AutoRun).where(AutoRun.status.in_(ACTIVE)).with_for_update(skip_locked=True).limit(500)
            )
        )
        .scalars()
        .all()
    )


async def screenshot(session: AsyncSession, owner_id: str, run_id: str, screenshot_id: str) -> AutoScreenshot | None:
    return (
        await session.execute(
            select(AutoScreenshot).where(
                AutoScreenshot.owner_id == owner_id,
                AutoScreenshot.run_id == run_id,
                AutoScreenshot.id == screenshot_id,
            )
        )
    ).scalar_one_or_none()


async def screenshots(session: AsyncSession, owner_id: str, run_id: str) -> Sequence[tuple[str, str, int]]:
    """(id, step, size) of a run's screenshots, oldest first; not the images."""
    return (
        await session.execute(
            select(AutoScreenshot.id, AutoScreenshot.step, AutoScreenshot.size)
            .where(AutoScreenshot.owner_id == owner_id, AutoScreenshot.run_id == run_id)
            .order_by(AutoScreenshot.id)
        )
    ).all()
