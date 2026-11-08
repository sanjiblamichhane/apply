"""
Matches: postings that passed a search's rules, scored by the model against a profile.

- A score is the model's 0–100 with up to three reasons and any dealbreakers, at temperature 0 and held to a
  JSON schema. If the model can't answer, the match says "not scored" with the reason: never a made-up number.
- A deterministic rule adds a dealbreaker when the search needs sponsorship and the posting says there is none.
- Scores are capped per owner per day (APPLY_SCORE_DAILY_CAP); past the cap they wait for tomorrow.
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument, NotFound
from apply.libs.jobs import JobContext
from apply.libs.llm import LLMError
from apply.packs import get_pack
from apply.packs.base import OpportunityInput, ProfileInput
from apply.runtime import Runtime
from apply.store.sql.models import Match
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import discovery as repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo

from . import applications, auto, background

logger = logging.getLogger("apply.logic.matches")

STATUSES = ("new", "saved", "dismissed", "tracked")
NO_SPONSORSHIP = {"code": "NO_SPONSORSHIP", "text": "The posting says it doesn't sponsor visas, and you need one."}


def start_of_day(now: datetime) -> datetime:
    return datetime.combine(now.date(), time(0), tzinfo=UTC)


def parse_score(data: dict[str, Any]) -> tuple[int, list[str], list[dict[str, str]]]:
    """The model's answer, held to its bounds: a number from 0 to 100, at most three short reasons."""
    try:
        score = int(data.get("fit_score"))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise LLMError(LLMError.BAD_REPLY, f"fit_score is not a number: {data.get('fit_score')!r}") from exc
    reasons = [str(r).strip()[:300] for r in data.get("reasons") or [] if str(r).strip()][:3]
    dealbreakers = [{"text": str(d).strip()[:300]} for d in data.get("dealbreakers") or [] if str(d).strip()][:3]
    return max(0, min(100, score)), reasons, dealbreakers


async def score(rt: Runtime, ctx: JobContext) -> None:
    """``match.score``: ask the model how well the profile fits the posting."""
    match_id = ctx.payload["match_id"]
    now = datetime.now(UTC)
    async with rt.db.transaction() as session:
        match = await repo.match_any_owner(session, match_id, for_update=True)
        if match is None or match.score_status not in ("pending", "capped") or match.status == "dismissed":
            return
        owner_id = match.owner_id
        if await repo.scored_since(session, owner_id, start_of_day(now)) >= rt.settings.score_daily_cap:
            match.score_status, match.score_error_code = "capped", ErrorCode.SCORE_CAP_REACHED.value
            await background.score_match(
                session,
                owner_id,
                match.id,
                key_suffix=":tomorrow",
                run_after=start_of_day(now) + timedelta(days=1, minutes=5),
            )
            return
        opp = await opportunities_repo.get(session, owner_id, match.opportunity_id)
        pack = get_pack(opp.pack)
        profile = None
        if match.profile_id:
            profile = await _profile(session, owner_id, match.profile_id)
        profile = profile or await profiles_repo.default_for(session, owner_id, opp.pack)
        if profile is None:
            match.score_status, match.score_error_code = "failed", ErrorCode.PROFILE_REQUIRED.value
            return
        prompt = pack.score_prompt(
            ProfileInput(name=profile.name, summary=profile.summary, attributes=profile.attributes),
            OpportunityInput(
                title=opp.title, issuer_name=opp.issuer_name, attributes=opp.attributes, source_text=opp.source_text
            ),
        )
        profile_id, no_sponsorship = profile.id, bool(match.prefilter.get("no_sponsorship"))

    try:
        data = await rt.model.complete_json(prompt.text, pack.score_schema, purpose=prompt.purpose)
        value, reasons, dealbreakers = parse_score(data)
        error = None
    except LLMError as exc:
        logger.warning("matches: the model could not score %s: %s", match_id, exc)
        value, reasons, dealbreakers, error = None, [], [], exc.code

    async with rt.db.transaction() as session:
        match = await repo.match_any_owner(session, match_id, for_update=True)
        if match is None:
            return
        if no_sponsorship:
            dealbreakers = [NO_SPONSORSHIP, *dealbreakers]
        match.profile_id = profile_id
        match.model = rt.model.model_for(prompt.purpose)
        if error:
            match.score_status, match.score_error_code = "failed", error
        else:
            match.score, match.score_reasons, match.dealbreakers = value, reasons, dealbreakers
            match.score_status, match.score_error_code, match.scored_at = "scored", None, datetime.now(UTC)
            await auto.consider(session, rt.settings, match)  # a strong match on an Auto search starts a run


async def _profile(session: AsyncSession, owner_id: str, profile_id: str):
    try:
        return await profiles_repo.get(session, owner_id, profile_id)
    except NotFound:
        return None


async def give_up_scoring(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        match = await repo.match_any_owner(session, ctx.payload["match_id"], for_update=True)
        if match is not None and match.score_status in ("pending", "capped"):
            match.score_status, match.score_error_code = "failed", ErrorCode.INTERNAL.value


# ── the inbox ────────────────────────────────────────────────────────────────


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
    for status in statuses:
        if status not in STATUSES:
            raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"No status {status!r}")
    if after and (":" not in after or not after.partition(":")[0].lstrip("-").isdigit()):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "That page cursor isn't one of ours")
    return await repo.inbox(
        session,
        owner_id,
        statuses=statuses,
        search_id=search_id,
        min_score=min_score,
        after=after,
        limit=limit,
        pack=pack,
    )


async def set_status(session: AsyncSession, owner_id: str, match_id: str, status: str) -> Match:
    if status not in ("new", "saved", "dismissed"):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "A match can be new, saved or dismissed here")
    match = await repo.match(session, owner_id, match_id, for_update=True)
    if match.status == "tracked":
        raise Conflict(
            ErrorCode.APPLICATION_EXISTS,
            "This match is an application now",
            extra={"application_id": match.application_id},
        )
    match.status, match.status_changed_at = status, datetime.now(UTC)
    if status != "dismissed" and match.score_status == "pending":
        await background.score_match(session, owner_id, match.id)
    await session.flush()
    return await repo.match_loaded(session, owner_id, match_id)


async def track(session: AsyncSession, owner_id: str, match_id: str) -> tuple[Match, str]:
    """Turn a match into an application (or point it at the one already tracking the job)."""
    match = await repo.match(session, owner_id, match_id, for_update=True)
    existing = await applications_repo.by_opportunity(session, owner_id, match.opportunity_id)
    if existing is not None:
        application_id = existing.id
    else:
        application = await applications.create(
            session, owner_id, opportunity_id=match.opportunity_id, profile_id=match.profile_id
        )
        application_id = application.id
    match.status, match.application_id, match.status_changed_at = "tracked", application_id, datetime.now(UTC)
    await session.flush()
    return await repo.match_loaded(session, owner_id, match_id), application_id


async def counts(session: AsyncSession, owner_id: str, pack: str | None = None) -> dict[str, int]:
    return await repo.counts(session, owner_id, pack)
