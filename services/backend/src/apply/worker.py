"""
The background worker: ``apply worker --queue llm --concurrency 1`` for model work (a local model server answers one
at a time), ``apply worker --queue default`` for the rest, or ``apply worker`` for both in one process.
"""

import asyncio
import contextlib
import logging
import signal
from datetime import UTC, datetime, timedelta

from apply.libs.jobs import Handler, JobContext, Periodic, Worker
from apply.logic import (
    auto,
    background,
    briefings,
    claims,
    documents,
    files,
    matches,
    opportunities,
    profiles,
    review,
    scheduler,
    searches,
    sources,
)
from apply.logic import packs as packs_logic
from apply.runtime import Runtime
from apply.store.sql.repo import users as users_repo

logger = logging.getLogger("apply.worker")

SWEEP_SECONDS = 6 * 3600


def handlers(rt: Runtime) -> dict[str, Handler]:
    """Every job kind apply runs, bound to a runtime."""
    # A model call may take up to llm_timeout; the lease is renewed while it runs, so this is only how soon a
    # dead worker's job is picked up again.
    lease = min(rt.settings.llm_timeout + 60, 600)
    return {
        background.GENERATE_DOCUMENT: Handler(
            run=lambda ctx: documents.write(rt, ctx),
            on_give_up=lambda ctx: documents.give_up(rt, ctx),
            lease_seconds=lease,
        ),
        background.EXTRACT_OPPORTUNITY: Handler(
            run=lambda ctx: opportunities.extract_with_model(rt, ctx),
            on_give_up=lambda ctx: opportunities.give_up_extraction(rt, ctx),
            lease_seconds=lease,
        ),
        background.SCORE_MATCH: Handler(
            run=lambda ctx: matches.score(rt, ctx),
            on_give_up=lambda ctx: matches.give_up_scoring(rt, ctx),
            lease_seconds=lease,
        ),
        background.CHECK_DOCUMENT: Handler(
            run=lambda ctx: claims.check(rt, ctx),
            on_give_up=lambda ctx: claims.give_up(rt, ctx),
            lease_seconds=lease,
        ),
        background.READ_PROFILE: Handler(
            run=lambda ctx: profiles.read(rt, ctx),
            on_give_up=lambda ctx: profiles.give_up_reading(rt, ctx),
            lease_seconds=lease,
        ),
        background.RENDER_DOCUMENT: Handler(run=lambda ctx: review.render(rt, ctx), lease_seconds=120),
        background.FETCH_SOURCE: Handler(run=lambda ctx: sources.fetch(rt, ctx), lease_seconds=300),
        background.RUN_SEARCH: Handler(run=lambda ctx: _run_search(rt, ctx), lease_seconds=300),
        background.BUILD_BRIEFING: Handler(run=lambda ctx: _build_briefing(rt, ctx), lease_seconds=120),
        auto.ADVANCE: Handler(run=lambda ctx: auto.advance(rt, ctx), lease_seconds=120),
    }


async def _run_search(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        await searches.run(session, ctx.owner_id or "", ctx.payload["search_id"])


async def _build_briefing(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        await briefings.build(session, ctx.payload["owner_id"], ctx.payload["date"])


async def _sweep_accounts(rt: Runtime) -> None:
    async with rt.db.transaction() as session:
        await users_repo.delete_expired_sessions(session)
        await users_repo.delete_old_resets(session, datetime.now(UTC) - timedelta(days=1))


def build(
    rt: Runtime, *, queues: list[str], concurrency: int, name: str | None = None, schedule: bool = True
) -> Worker:
    """A worker for these queues; with ``schedule`` it also ticks the scheduler (several may: keys dedupe)."""
    periodic = (
        [
            Periodic(rt.settings.scheduler_tick_seconds, lambda: scheduler.tick(rt)),
            Periodic(SWEEP_SECONDS, lambda: files.sweep(rt)),  # files nothing points at any more
            Periodic(SWEEP_SECONDS, lambda: _sweep_accounts(rt)),  # ended sessions, old reset links
        ]
        if schedule
        else []
    )
    return Worker(
        rt.queue,
        handlers(rt),
        queues=queues,
        concurrency=concurrency,
        name=name,
        poll_seconds=rt.settings.worker_poll_seconds,
        listen_dsn=rt.db.dsn,
        periodic=periodic,
    )


async def run(rt: Runtime, *, queues: list[str], concurrency: int, once: bool = False) -> None:
    async with rt.db.transaction() as session:
        await packs_logic.sync(session)
    await rt.files.ensure()
    await files.move_from_database(rt)
    worker = build(rt, queues=queues, concurrency=concurrency)
    if once:
        await worker.run_until_idle()
        return
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    logger.info("worker %s: queues %s, concurrency %d", worker.name, queues, concurrency)
    await worker.run_forever(stop)
