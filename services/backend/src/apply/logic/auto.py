"""
Auto: strong matches are prepared for the person to send. Nothing is ever submitted by apply: no board offers
a candidate a sanctioned way to submit automatically (their submission APIs need the employer's key), and their
terms forbid automated access. So Auto does the slow part ahead and stops at "Ready for you"; the person opens
the application, the extension fills it, and they press Submit (docs/auto.md).

A run, one per match, moves through:

    starting → writing → ready → sent (when the person's submission is recorded)

or stops at ``needs_you`` (a stable reason code) or ``stopped`` (the person). ``auto.advance`` jobs move it
forward; the scheduler's tick sweeps up anything a crash left behind. The gate is checked at the start: not
paused, under the daily cap, nothing to the same issuer in 30 days, still open.

Runs from before (when a runner sent applications) keep what they recorded: their details and screenshots.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument
from apply.libs.jobs import JobContext, enqueue
from apply.packs import get_pack
from apply.runtime import Runtime
from apply.settings import AppSettings
from apply.store.sql.models import ApplicationDocument, AutoRun, Match, Opportunity, User, jobs
from apply.store.sql.repo import auto as repo
from apply.store.sql.repo import discovery as discovery_repo
from apply.store.sql.repo import documents as documents_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo
from apply.store.sql.repo import review as review_repo
from apply.store.sql.repo import users as users_repo

from . import background, briefings, documents
from .review import digest_of

logger = logging.getLogger("apply.logic.auto")

ADVANCE = "auto.advance"
SAME_ISSUER_DAYS = 30
# A run that ended with Submit pressed and no clear answer (when a runner sent): never started again.
MAY_HAVE_GONE = {ErrorCode.AUTO_SEND_UNKNOWN.value, ErrorCode.AUTO_NO_CONFIRMATION.value}


def _now() -> datetime:
    return datetime.now(UTC)


# ─── rules (pure) ────────────────────────────────────────────────────────────


SUFFIXES = re.compile(r"\b(inc|llc|ltd|limited|gmbh|co|corp|corporation|plc|pvt|private|company)\b\.?", re.I)


def issuer_key(name: str) -> str:
    """'Acme Robotics, Inc.' and 'acme robotics' are the same issuer."""
    return re.sub(r"[^a-z0-9]+", "", SUFFIXES.sub(" ", name.lower()))


def start_of_local_day(user: User, now: datetime) -> datetime:
    local = now.astimezone(briefings.zone(user))
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


# ─── scheduling ──────────────────────────────────────────────────────────────


async def schedule(session: AsyncSession, run: AutoRun, *, delay: float = 0.0) -> None:
    """Look at the run again after ``delay`` seconds. An older look still queued sees the revision and stops."""
    run.revision += 1
    await enqueue(
        session,
        jobs,
        kind=ADVANCE,
        queue=background.DEFAULT,
        priority=background.INTERACTIVE,
        max_attempts=3,
        key=f"auto:{run.id}:{run.revision}",
        owner_id=run.owner_id,
        run_after=_now() + timedelta(seconds=delay) if delay else None,
        payload={"run_id": run.id, "revision": run.revision},
    )


def _needs_you(run: AutoRun, code: ErrorCode, detail: dict[str, Any] | None = None) -> None:
    logger.info("auto: run %s needs you: %s %s", run.id, code, detail or "")
    run.status, run.reason, run.reason_detail = "needs_you", code.value, detail or {}
    run.finished_at = _now()


# ─── starting a run ──────────────────────────────────────────────────────────


async def consider(session: AsyncSession, settings: AppSettings, match: Match) -> AutoRun | None:
    """After a match is scored: start a run if it's strong and a search that found it has Auto on."""
    if match.score is None or match.status == "dismissed" or match.dealbreakers:
        return None
    user = await users_repo.by_id(session, match.owner_id)
    if user is None or match.score < user.auto_min_score:
        return None
    found = [await _search(session, match.owner_id, sid) for sid in match.search_ids or []]
    search = next((s for s in found if s is not None and s.enabled and s.auto_enabled), None)
    if search is None or not get_pack(search.pack).auto:
        return None
    if await repo.for_match(session, match.owner_id, match.id) is not None:
        return None
    run = AutoRun(
        owner_id=match.owner_id,
        match_id=match.id,
        search_id=search.id,
        status="starting",
        deadline_at=_now() + timedelta(minutes=settings.auto_wait_minutes),
    )
    session.add(run)
    await session.flush()
    await schedule(session, run)
    return run


async def _search(session: AsyncSession, owner_id: str, search_id: str):
    try:
        return await discovery_repo.search(session, owner_id, search_id)
    except Exception:  # noqa: BLE001 - deleted since
        return None


# ─── the gate ────────────────────────────────────────────────────────────────


async def gate(
    session: AsyncSession, settings: AppSettings, run: AutoRun, user: User, opp: Opportunity
) -> tuple[ErrorCode, dict[str, Any]] | None:
    if user.auto_paused:
        return ErrorCode.AUTO_PAUSED, {}
    if opp.status not in ("open", "rolling"):
        return ErrorCode.AUTO_CLOSED, {}
    now = _now()
    prepared = await repo.ready_since(session, user.id, start_of_local_day(user, now), not_id=run.id)
    if prepared >= user.auto_daily_cap:
        return ErrorCode.AUTO_CAP_REACHED, {"cap": user.auto_daily_cap}
    key = issuer_key(opp.issuer_name)
    if key:
        since = now - timedelta(days=SAME_ISSUER_DAYS)
        for name, why in await repo.issuer_activity(session, user.id, since=since, not_application=run.application_id):
            if issuer_key(name) == key:
                return ErrorCode.AUTO_SAME_ISSUER, {"issuer": opp.issuer_name, "why": why}
    return None


# ─── moving a run along ──────────────────────────────────────────────────────


async def advance(rt: Runtime, ctx: JobContext) -> None:
    """``auto.advance``: one step of a run, if this look is still the current one."""
    async with rt.db.transaction() as session:
        run = await repo.run_any_owner(session, ctx.payload["run_id"], for_update=True)
        if run is None or run.revision != ctx.payload.get("revision"):
            return
        await step(session, rt.settings, run)


async def step(session: AsyncSession, settings: AppSettings, run: AutoRun) -> None:
    user = await users_repo.by_id(session, run.owner_id)
    match = await discovery_repo.match(session, run.owner_id, run.match_id)
    opp = await opportunities_repo.get(session, run.owner_id, match.opportunity_id)
    assert user is not None
    now = _now()

    if run.status == "starting":
        if (blocked := await gate(session, settings, run, user, opp)) is not None:
            return _needs_you(run, *blocked)
        if await profiles_repo.default_for(session, run.owner_id, opp.pack) is None and match.profile_id is None:
            return _needs_you(run, ErrorCode.AUTO_PROFILE_REQUIRED)
        from . import matches as matches_logic  # matches starts runs: imported here, not at the top

        _, application_id = await matches_logic.track(session, run.owner_id, match.id)
        run.application_id = application_id
        have = {d.document_type for d in await _current(session, run.owner_id, application_id)}
        for spec in get_pack(opp.pack).document_types:
            if spec.generatable and spec.key not in have:
                await documents.request(session, run.owner_id, application_id, document_type=spec.key, profile_id=None)
        run.status = "writing"
        return await schedule(session, run, delay=settings.auto_poll_seconds)

    if run.status == "writing":
        assert run.application_id
        pack = get_pack(opp.pack)
        wanted = [s.key for s in pack.document_types if s.generatable]
        all_docs = await documents_repo.of_application(session, run.owner_id, run.application_id)
        ready = {d.document_type: d for d in all_docs if d.is_active and d.status == "ready"}
        pending = [d for d in all_docs if d.status == "pending"]
        failed = [t for t in wanted if t not in ready and not any(d.document_type == t for d in pending)]
        if failed:
            return _needs_you(run, ErrorCode.AUTO_DOCUMENT_FAILED, {"documents": failed})
        docs = [ready[t] for t in wanted if t in ready]
        rendered = [await review_repo.rendered(session, d.id, "pdf", await digest_of(session, d)) for d in docs]
        if pending or len(docs) < len(wanted) or any(d.claims_status == "pending" for d in docs) or None in rendered:
            if run.deadline_at and now > run.deadline_at:
                return _needs_you(run, ErrorCode.AUTO_TIMED_OUT, {"step": "writing"})
            return await schedule(session, run, delay=settings.auto_poll_seconds)
        if any(d.claims_status == "skipped" for d in docs):
            return _needs_you(run, ErrorCode.AUTO_PROFILE_REQUIRED)
        if any(d.claims_status == "failed" for d in docs):
            return _needs_you(run, ErrorCode.AUTO_CLAIMS_UNCHECKED)
        open_warnings = sum(1 for d in docs for w in d.claim_warnings if not w.get("resolved"))
        if open_warnings:
            return _needs_you(run, ErrorCode.AUTO_CLAIM_WARNINGS, {"count": open_warnings})
        # Prepared: the person sends it (Open the application; the extension fills; they press Submit).
        run.status, run.ready_at, run.deadline_at = "ready", now, None
        return None


async def _current(session: AsyncSession, owner_id: str, application_id: str) -> list[ApplicationDocument]:
    return [
        d
        for d in await documents_repo.of_application(session, owner_id, application_id)
        if d.is_active and d.status == "ready"
    ]


# ─── the person's side ───────────────────────────────────────────────────────


async def stop(session: AsyncSession, owner_id: str, run_id: str) -> AutoRun:
    """Stop preparing it, or take it off Ready for you. Its application and documents stay."""
    run = await repo.run(session, owner_id, run_id, for_update=True)
    if run.status not in (*repo.ACTIVE, "ready"):
        raise Conflict(ErrorCode.AUTO_ACTION_NOT_ALLOWED, f"A {run.status} run can't be stopped")
    run.status, run.finished_at = "stopped", _now()
    return run


async def retry(session: AsyncSession, settings: AppSettings, owner_id: str, run_id: str) -> AutoRun:
    """Start again from the gate (after the person fixed what it needed). Never after an uncertain send."""
    run = await repo.run(session, owner_id, run_id, for_update=True)
    if run.status not in ("needs_you", "stopped") or run.reason in MAY_HAVE_GONE:
        raise Conflict(ErrorCode.AUTO_ACTION_NOT_ALLOWED, "This run can't be tried again")
    if run.submission_id:
        raise Conflict(ErrorCode.AUTO_ACTION_NOT_ALLOWED, "This one was sent")
    run.status, run.reason, run.reason_detail = "starting", None, {}
    run.ready_at = run.finished_at = None
    run.deadline_at = _now() + timedelta(minutes=settings.auto_wait_minutes)
    await schedule(session, run)
    return run


async def dismiss(session: AsyncSession, owner_id: str, run_id: str) -> AutoRun:
    run = await repo.run(session, owner_id, run_id, for_update=True)
    if run.status not in ("needs_you", "stopped"):
        raise Conflict(ErrorCode.AUTO_ACTION_NOT_ALLOWED, "Only a run that needs you can be dismissed")
    run.status = "dismissed"
    return run


# ─── settings ────────────────────────────────────────────────────────────────

LIMITS = {"auto_min_score": (0, 100), "auto_daily_cap": (0, 50)}


async def update_settings(session: AsyncSession, owner_id: str, changes: dict[str, Any]) -> User:
    user = await users_repo.by_id(session, owner_id)
    assert user is not None
    for key, (low, high) in LIMITS.items():
        if changes.get(key) is not None:
            value = changes[key]
            if not low <= value <= high:
                raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"{key} is from {low} to {high}")
            setattr(user, key, value)
    if changes.get("auto_paused") is not None:
        user.auto_paused = bool(changes["auto_paused"])
    await session.flush()
    return user


# ─── the sweep (scheduler tick) ──────────────────────────────────────────────


async def sweep(session: AsyncSession, settings: AppSettings, now: datetime | None = None) -> int:
    """What a crash leaves behind: a look that was lost (looked at again)."""
    now = now or _now()
    touched = 0
    quiet = timedelta(seconds=settings.auto_poll_seconds * 4 + 60)
    for run in await repo.to_sweep(session, now):
        if run.status in ("starting", "writing") and now - run.updated_at > quiet:
            await schedule(session, run)
            touched += 1
    return touched
