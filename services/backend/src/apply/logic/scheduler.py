"""
Recurring work, without a beat process: the worker calls ``tick`` every minute (plan §6). It only enqueues; the
jobs do the work. Job keys make it safe to tick from several workers at once: a source or briefing already
waiting or running isn't queued twice.
"""

import logging
from datetime import UTC, datetime

from apply.runtime import Runtime
from apply.store.sql.repo import discovery as repo

from . import auto, background, briefings, matches, sources

logger = logging.getLogger("apply.logic.scheduler")


async def tick(rt: Runtime, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    queued = {"sources": 0, "briefings": 0, "scores": 0, "auto": 0}
    async with rt.db.transaction() as session:
        for source in await repo.enabled_sources(session):
            if sources.due(source, now) and await background.fetch_source(session, source.owner_id, source.id):
                queued["sources"] += 1

        for user in await repo.users(session):
            date = briefings.local_date(user, now)
            has_today = await repo.briefing(session, user.id, date) is not None
            if briefings.due(user, now, has_today) and await background.build_briefing(session, user.id, date):
                queued["briefings"] += 1

        # Matches whose scoring job was lost (a crash) or held over by yesterday's cap, up to today's room.
        for owner_id in await repo.owners_with_waiting_scores(session):
            room = rt.settings.score_daily_cap - await repo.scored_since(session, owner_id, matches.start_of_day(now))
            for match in await repo.waiting_to_score(session, owner_id, max(0, room)):
                if match.score_status == "capped":
                    match.score_status = "pending"
                if await background.score_match(session, owner_id, match.id):
                    queued["scores"] += 1

        # Auto runs a crash or a missing runner left behind.
        queued["auto"] = await auto.sweep(session, rt.settings, now)
    if any(queued.values()):
        logger.info("scheduler: queued %s", queued)
    return queued
