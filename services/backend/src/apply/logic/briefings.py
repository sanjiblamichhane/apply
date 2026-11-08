"""
The daily briefing, shown as Today: new matches since the last briefing (the best five), applications due a
follow-up, and deadlines in the next week. Built once a day per owner at their hour (logic/scheduler.py), or
on demand.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apply.store.sql.models import Application, Briefing, StageHistory, User
from apply.store.sql.repo import discovery as repo

TOP = 5
DEADLINE_DAYS = 7


def zone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.time_zone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_date(user: User, now: datetime) -> str:
    return now.astimezone(zone(user)).date().isoformat()


def due(user: User, now: datetime, has_today: bool) -> bool:
    """The owner's briefing hour has come today, in their time zone, and today's isn't built yet."""
    return not has_today and now.astimezone(zone(user)).hour >= user.briefing_hour


async def build(session: AsyncSession, owner_id: str, date: str, now: datetime | None = None) -> Briefing:
    now = now or datetime.now(UTC)
    previous = await repo.latest_briefing(session, owner_id, before=date)
    since = previous.created_at if previous else now - timedelta(days=1)
    matches = await repo.matches_since(session, owner_id, since)
    content: dict[str, Any] = {
        "new_matches": {
            "count": len(matches),
            "top": [
                {
                    "match_id": m.id,
                    "opportunity_id": m.opportunity_id,
                    "pack": m.opportunity.pack,
                    "title": m.opportunity.title,
                    "issuer_name": m.opportunity.issuer_name,
                    "score": m.score,
                }
                for m in matches[:TOP]
            ],
        },
        "follow_ups": await _follow_ups(session, owner_id, now),
        "deadlines": await _deadlines(session, owner_id, now),
    }
    found = await repo.briefing(session, owner_id, date)
    if found is None:
        found = Briefing(owner_id=owner_id, date=date, content=content)
        session.add(found)
    else:
        found.content = content
    await session.flush()
    return found


async def _follow_ups(session: AsyncSession, owner_id: str, now: datetime) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Application, StageHistory)
            .options(selectinload(Application.opportunity), selectinload(Application.stage))
            .join(StageHistory, (StageHistory.application_id == Application.id) & StageHistory.exited_at.is_(None))
            .where(Application.owner_id == owner_id)
        )
    ).all()
    out = []
    for app, entry in rows:
        days = app.stage.follow_up_after_days
        if days and not app.stage.is_terminal and entry.entered_at + timedelta(days=days) <= now:
            out.append(
                {
                    "application_id": app.id,
                    "pack": app.opportunity.pack,
                    "title": app.opportunity.title,
                    "issuer_name": app.opportunity.issuer_name,
                    "stage_code": app.stage.code,
                    "days": (now - entry.entered_at).days,
                }
            )
    return sorted(out, key=lambda f: -f["days"])


async def _deadlines(session: AsyncSession, owner_id: str, now: datetime) -> list[dict[str, Any]]:
    apps = (
        (
            await session.execute(
                select(Application)
                .options(selectinload(Application.opportunity), selectinload(Application.stage))
                .where(Application.owner_id == owner_id)
            )
        )
        .scalars()
        .all()
    )
    soon = now + timedelta(days=DEADLINE_DAYS)
    out = [
        {
            "application_id": a.id,
            "pack": a.opportunity.pack,
            "title": a.opportunity.title,
            "issuer_name": a.opportunity.issuer_name,
            "deadline": a.opportunity.deadline.isoformat(),
        }
        for a in apps
        if a.opportunity.deadline and now <= a.opportunity.deadline <= soon and not a.stage.is_terminal
    ]
    return sorted(out, key=lambda d: d["deadline"])


async def today(session: AsyncSession, owner_id: str, user: User) -> Briefing | None:
    return await repo.briefing(session, owner_id, local_date(user, datetime.now(UTC)))
