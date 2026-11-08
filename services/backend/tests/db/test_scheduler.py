"""The scheduler: due work is queued once, however many workers tick at the same moment."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from apply.logic import scheduler
from apply.store.sql.models import Source, User, jobs
from apply.store.sql.repo import users
from tests.conftest import add_account


async def test_two_ticks_at_once_queue_each_due_thing_once(rt):
    await add_account(rt, "a@example.com", "a long enough password")
    async with rt.db.transaction() as session:
        owner = await users.by_email(session, "a@example.com")
        owner.briefing_hour = 0
        now = datetime.now(UTC)
        session.add_all(
            [
                Source(owner_id=owner.id, pack="job", kind="board01", name="due", config={"board": "a"}),
                Source(
                    owner_id=owner.id,
                    pack="job",
                    kind="board02",
                    name="recent",
                    config={"company": "b"},
                    last_fetched_at=now - timedelta(minutes=10),
                ),
                Source(
                    owner_id=owner.id,
                    pack="tender",
                    kind="contracts_finder",
                    name="too soon for its terms",
                    config={},
                    interval_hours=1,
                    last_fetched_at=now - timedelta(hours=2),
                ),
            ]
        )
    results = await asyncio.gather(scheduler.tick(rt), scheduler.tick(rt), scheduler.tick(rt))
    assert sum(r["sources"] for r in results) == 1
    assert sum(r["briefings"] for r in results) == 1
    async with rt.db.engine.connect() as conn:
        kinds = dict((await conn.execute(select(jobs.c.kind, func.count()).group_by(jobs.c.kind))).all())
    assert kinds == {"source.fetch": 1, "briefing.build": 1}


async def test_a_briefing_waits_for_its_hour(rt):
    await add_account(rt, "a@example.com", "a long enough password")
    async with rt.db.transaction() as session:
        owner = await users.by_email(session, "a@example.com")
        owner.time_zone, owner.briefing_hour = "UTC", 23
    early = datetime.now(UTC).replace(hour=1)
    assert (await scheduler.tick(rt, now=early))["briefings"] == 0
    async with rt.db.transaction() as session:
        assert (await session.execute(select(func.count()).select_from(User))).scalar_one() == 1
