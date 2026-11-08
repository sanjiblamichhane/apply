"""Sources, searches, matches and briefings."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apply.errors import ErrorCode, NotFound

from ..db import new_id
from ..models import Briefing, Match, Opportunity, Search, Source, User
from . import MAX_PAGE, get_owned

# ── sources ──────────────────────────────────────────────────────────────────


async def source(session: AsyncSession, owner_id: str, source_id: str, *, for_update: bool = False) -> Source:
    return await get_owned(session, Source, owner_id, source_id, ErrorCode.SOURCE_NOT_FOUND, for_update=for_update)


async def source_any_owner(session: AsyncSession, source_id: str, *, for_update: bool = False) -> Source | None:
    stmt = select(Source).where(Source.id == source_id)
    if for_update:
        stmt = stmt.with_for_update(skip_locked=True)
    return (await session.execute(stmt)).scalar_one_or_none()


async def sources(session: AsyncSession, owner_id: str, pack: str | None = None) -> Sequence[Source]:
    stmt = select(Source).where(Source.owner_id == owner_id).order_by(Source.id)
    if pack:
        stmt = stmt.where(Source.pack == pack)
    return (await session.execute(stmt)).scalars().all()


async def enabled_sources(session: AsyncSession) -> Sequence[Source]:
    """Every source that's on, in accounts that are on (a turned-off account is asked nothing for)."""
    stmt = (
        select(Source)
        .join(User, User.id == Source.owner_id)
        .where(Source.enabled.is_(True), User.disabled_at.is_(None))
    )
    return (await session.execute(stmt)).scalars().all()


# ── searches ─────────────────────────────────────────────────────────────────


async def search(session: AsyncSession, owner_id: str, search_id: str, *, for_update: bool = False) -> Search:
    return await get_owned(session, Search, owner_id, search_id, ErrorCode.SEARCH_NOT_FOUND, for_update=for_update)


async def searches(
    session: AsyncSession, owner_id: str, pack: str | None = None, *, enabled_only: bool = False
) -> Sequence[Search]:
    stmt = select(Search).where(Search.owner_id == owner_id).order_by(Search.id)
    if pack:
        stmt = stmt.where(Search.pack == pack)
    if enabled_only:
        stmt = stmt.where(Search.enabled.is_(True))
    return (await session.execute(stmt)).scalars().all()


# ── opportunities from sources ───────────────────────────────────────────────


async def opportunity_by_dedupe(session: AsyncSession, owner_id: str, key: str) -> Opportunity | None:
    return (
        await session.execute(
            select(Opportunity)
            .where(Opportunity.owner_id == owner_id, Opportunity.dedupe_key == key)
            .order_by(Opportunity.id)
            .limit(1)
        )
    ).scalar_one_or_none()


async def close_unlisted(session: AsyncSession, source_id: str, seen: set[str]) -> int:
    """Postings this source no longer lists are closed (their matches stay, labelled)."""
    stmt = update(Opportunity).where(Opportunity.source_id == source_id, Opportunity.status == "open")
    if seen:
        stmt = stmt.where(Opportunity.id.not_in(seen))
    result = await session.execute(stmt.values(status="closed"))
    return result.rowcount or 0


async def opportunities_of(session: AsyncSession, owner_id: str, pack: str) -> Sequence[Opportunity]:
    return (
        (
            await session.execute(
                select(Opportunity).where(
                    Opportunity.owner_id == owner_id, Opportunity.pack == pack, Opportunity.status == "open"
                )
            )
        )
        .scalars()
        .all()
    )


# ── matches ──────────────────────────────────────────────────────────────────


async def upsert_match(
    session: AsyncSession,
    *,
    owner_id: str,
    opportunity_id: str,
    search_id: str,
    prefilter: dict[str, Any],
    profile_id: str | None,
) -> tuple[Match, bool]:
    """The one match for this opportunity, with this search added. Returns it and whether it is new."""
    inserted = (
        await session.execute(
            insert(Match)
            .values(
                id=new_id(),
                owner_id=owner_id,
                opportunity_id=opportunity_id,
                search_ids=[search_id],
                prefilter=prefilter,
                profile_id=profile_id,
            )
            .on_conflict_do_nothing(index_elements=[Match.owner_id, Match.opportunity_id])
            .returning(Match.id)
        )
    ).scalar_one_or_none()
    found = (
        await session.execute(
            select(Match).where(Match.owner_id == owner_id, Match.opportunity_id == opportunity_id).with_for_update()
        )
    ).scalar_one()
    if inserted is None and search_id not in found.search_ids:
        found.search_ids = [*found.search_ids, search_id]
    return found, inserted is not None


async def match(session: AsyncSession, owner_id: str, match_id: str, *, for_update: bool = False) -> Match:
    return await get_owned(session, Match, owner_id, match_id, ErrorCode.MATCH_NOT_FOUND, for_update=for_update)


async def match_loaded(session: AsyncSession, owner_id: str, match_id: str) -> Match:
    found = (
        await session.execute(
            select(Match)
            .options(selectinload(Match.opportunity))
            .where(Match.id == match_id, Match.owner_id == owner_id)
        )
    ).scalar_one_or_none()
    if found is None:
        raise NotFound(ErrorCode.MATCH_NOT_FOUND, "No such match for this owner")
    return found


async def match_any_owner(session: AsyncSession, match_id: str, *, for_update: bool = False) -> Match | None:
    stmt = select(Match).where(Match.id == match_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


def _rank() -> Any:
    return func.coalesce(Match.score, -1)


async def inbox(
    session: AsyncSession,
    owner_id: str,
    *,
    statuses: list[str],
    search_id: str | None,
    min_score: int | None,
    after: str | None,
    limit: int,
    pack: str | None = None,
) -> tuple[Sequence[Match], str | None]:
    """Best first (unscored last), then newest; keyset pages on (score, id)."""
    limit = max(1, min(limit, MAX_PAGE))
    stmt: Select[Any] = (
        select(Match)
        .options(selectinload(Match.opportunity))
        .where(Match.owner_id == owner_id, Match.status.in_(statuses))
    )
    if search_id:
        stmt = stmt.where(Match.search_ids.contains([search_id]))
    if pack:
        stmt = stmt.where(Match.opportunity_id.in_(select(Opportunity.id).where(Opportunity.pack == pack)))
    if min_score is not None:
        stmt = stmt.where(Match.score >= min_score)
    if after:
        score_text, _, last_id = after.partition(":")
        last_score = int(score_text)
        stmt = stmt.where(or_(_rank() < last_score, and_(_rank() == last_score, Match.id < last_id)))
    rows = (await session.execute(stmt.order_by(_rank().desc(), Match.id.desc()).limit(limit + 1))).scalars().all()
    more = len(rows) > limit
    rows = rows[:limit]
    cursor = None
    if more and rows:
        last = rows[-1]
        cursor = f"{last.score if last.score is not None else -1}:{last.id}"
    return rows, cursor


async def counts(session: AsyncSession, owner_id: str, pack: str | None = None) -> dict[str, int]:
    stmt = select(Match.status, func.count()).where(Match.owner_id == owner_id)
    if pack:
        stmt = stmt.where(Match.opportunity_id.in_(select(Opportunity.id).where(Opportunity.pack == pack)))
    rows = (await session.execute(stmt.group_by(Match.status))).all()
    return {"new": 0, "saved": 0, "dismissed": 0, "tracked": 0} | {r[0]: r[1] for r in rows}


async def scored_since(session: AsyncSession, owner_id: str, since: datetime) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(Match)
            .where(Match.owner_id == owner_id, Match.scored_at >= since, Match.score_status == "scored")
        )
    ).scalar_one()


async def waiting_to_score(session: AsyncSession, owner_id: str, limit: int) -> Sequence[Match]:
    return (
        (
            await session.execute(
                select(Match)
                .where(
                    Match.owner_id == owner_id,
                    Match.score_status.in_(("pending", "capped")),
                    Match.status != "dismissed",
                )
                .order_by(Match.id)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def owners_with_waiting_scores(session: AsyncSession) -> Sequence[str]:
    return (
        (await session.execute(select(Match.owner_id).where(Match.score_status.in_(("pending", "capped"))).distinct()))
        .scalars()
        .all()
    )


# ── briefings ────────────────────────────────────────────────────────────────


async def users(session: AsyncSession) -> Sequence[User]:
    """The accounts that get a briefing: those that are on."""
    return (await session.execute(select(User).where(User.disabled_at.is_(None)))).scalars().all()


async def briefing(session: AsyncSession, owner_id: str, date: str) -> Briefing | None:
    return (
        await session.execute(select(Briefing).where(Briefing.owner_id == owner_id, Briefing.date == date))
    ).scalar_one_or_none()


async def latest_briefing(session: AsyncSession, owner_id: str, before: str | None = None) -> Briefing | None:
    stmt = select(Briefing).where(Briefing.owner_id == owner_id)
    if before:
        stmt = stmt.where(Briefing.date < before)
    return (await session.execute(stmt.order_by(Briefing.date.desc()).limit(1))).scalar_one_or_none()


async def matches_since(session: AsyncSession, owner_id: str, since: datetime | None) -> Sequence[Match]:
    stmt = (
        select(Match)
        .options(selectinload(Match.opportunity))
        .where(Match.owner_id == owner_id, Match.status.in_(("new", "saved")))
    )
    if since is not None:
        stmt = stmt.where(Match.created_at >= since)
    return (await session.execute(stmt.order_by(_rank().desc(), Match.id.desc()))).scalars().all()
