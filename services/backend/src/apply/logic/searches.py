"""
Saved searches: the rules that pick postings worth a look, before any model is asked.

The prefilter is deterministic and free: keywords (any or all), words that rule a posting out, places, remote
only. Only what passes goes on to the model's fit score (logic/matches.py).
"""

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, InvalidArgument
from apply.packs import get_pack
from apply.packs.base import Searchable
from apply.store.sql.models import Opportunity, Search
from apply.store.sql.repo import discovery as repo
from apply.store.sql.repo import profiles as profiles_repo

from . import background


class Criteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keywords: list[str] = Field(default_factory=list, max_length=30)
    match_all: bool = False
    exclude: list[str] = Field(default_factory=list, max_length=30)
    locations: list[str] = Field(default_factory=list, max_length=20)
    remote_only: bool = False
    needs_sponsorship: bool = False
    source_ids: list[str] = Field(default_factory=list, max_length=50)  # empty: every source

    @field_validator("keywords", "exclude", "locations")
    @classmethod
    def _clean(cls, values: list[str]) -> list[str]:
        return [v.strip()[:80] for v in values if v and v.strip()]


def parse(criteria: dict[str, Any]) -> Criteria:
    try:
        return Criteria.model_validate(criteria)
    except ValidationError as exc:
        errors = [{"loc": ["criteria", *e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        raise InvalidArgument(
            ErrorCode.VALIDATION_FAILED, "The search's rules don't fit", extra={"errors": errors}
        ) from exc


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _has(haystack: str, phrase: str) -> bool:
    """A word or phrase, whole: "go" doesn't match "good", "c++" matches "C++"."""
    needle = re.escape(_plain(phrase))
    return re.search(rf"(?<![a-z0-9]){needle}(?![a-z0-9])", haystack) is not None


NO_SPONSORSHIP = re.compile(
    r"(no|not|unable to|cannot|can't|will not|won't|does not|doesn't)\s+(offer\s+|provide\s+)?(visa\s+)?sponsor"
    r"|without\s+(visa\s+)?sponsorship|citizens?\s+only|must\s+be\s+(a\s+)?(us\s+|u\.s\.\s+)?citizen",
    re.IGNORECASE,
)


def says_no_sponsorship(text: str) -> bool:
    return bool(NO_SPONSORSHIP.search(text))


def evaluate(criteria: Criteria, item: Searchable) -> tuple[bool, dict[str, Any]]:
    """Whether a posting passes the rules, and which words or places made it pass (shown with the match)."""
    title, text = _plain(item.title), _plain(f"{item.title}\n{item.body}")
    found = [k for k in criteria.keywords if _has(text, k)]
    if criteria.keywords:
        if criteria.match_all and len(found) < len(criteria.keywords):
            return False, {}
        if not found:
            return False, {}
    excluded = [w for w in criteria.exclude if _has(title, w)]
    if excluded:
        return False, {}
    if criteria.remote_only and not item.remote:
        return False, {}
    place = _plain(item.location)
    places = [p for p in criteria.locations if _plain(p) in place]
    if criteria.locations and not places and not item.remote:
        return False, {}
    return True, {"keywords": found, "locations": places, "remote": item.remote}


# ── reading and changing searches ────────────────────────────────────────────


async def create(
    session: AsyncSession,
    owner_id: str,
    *,
    pack: str,
    name: str,
    criteria: dict[str, Any],
    profile_id: str | None,
    min_score: int,
    enabled: bool,
    auto_enabled: bool = False,
) -> Search:
    get_pack(pack)
    clean = parse(criteria)
    await _check_refs(session, owner_id, clean, profile_id)
    search = Search(
        owner_id=owner_id,
        pack=pack,
        name=name,
        criteria=clean.model_dump(),
        profile_id=profile_id,
        min_score=min_score,
        enabled=enabled,
        auto_enabled=auto_enabled,
    )
    session.add(search)
    await session.flush()
    await background.run_search(session, owner_id, search.id)
    return search


async def update(session: AsyncSession, owner_id: str, search_id: str, changes: dict[str, Any]) -> Search:
    search = await repo.search(session, owner_id, search_id, for_update=True)
    if "criteria" in changes and changes["criteria"] is not None:
        clean = parse(changes["criteria"])
        await _check_refs(session, owner_id, clean, None)
        search.criteria = clean.model_dump()
    if "profile_id" in changes:
        if changes["profile_id"]:
            await profiles_repo.get(session, owner_id, changes["profile_id"])
        search.profile_id = changes["profile_id"]
    for key in ("name", "min_score", "enabled", "auto_enabled"):
        if key in changes and changes[key] is not None:
            setattr(search, key, changes[key])
    await session.flush()
    if search.enabled:
        await background.run_search(session, owner_id, search.id)
    return search


async def delete(session: AsyncSession, owner_id: str, search_id: str) -> None:
    search = await repo.search(session, owner_id, search_id, for_update=True)
    await session.delete(search)


async def _check_refs(session: AsyncSession, owner_id: str, criteria: Criteria, profile_id: str | None) -> None:
    for source_id in criteria.source_ids:
        await repo.source(session, owner_id, source_id)
    if profile_id:
        await profiles_repo.get(session, owner_id, profile_id)


async def list_(session: AsyncSession, owner_id: str, pack: str | None) -> Sequence[Search]:
    return await repo.searches(session, owner_id, pack)


async def get(session: AsyncSession, owner_id: str, search_id: str) -> Search:
    return await repo.search(session, owner_id, search_id)


# ── matching ─────────────────────────────────────────────────────────────────


async def match_opportunities(
    session: AsyncSession,
    owner_id: str,
    opportunities: Sequence[Opportunity],
    *,
    searches: Sequence[Search] | None = None,
) -> int:
    """Run the owner's enabled searches over these opportunities: a match for each that passes, scored later."""
    if not opportunities:
        return 0
    searches = searches if searches is not None else await repo.searches(session, owner_id, enabled_only=True)
    made = 0
    for search in searches:
        if not search.enabled:
            continue
        pack = get_pack(search.pack)
        criteria = Criteria.model_validate(search.criteria)
        for opp in opportunities:
            if opp.pack != search.pack or opp.status != "open":
                continue
            if criteria.source_ids and opp.source_id not in criteria.source_ids:
                continue
            item = pack.searchable(opp.title, opp.attributes)
            passed, why = evaluate(criteria, item)
            if not passed:
                continue
            if criteria.needs_sponsorship and says_no_sponsorship(f"{item.sponsorship}\n{item.body}"):
                why = {**why, "no_sponsorship": True}
            match, new = await repo.upsert_match(
                session,
                owner_id=owner_id,
                opportunity_id=opp.id,
                search_id=search.id,
                prefilter=why,
                profile_id=search.profile_id,
            )
            if new:
                made += 1
                await background.score_match(session, owner_id, match.id)
    return made


async def run(session: AsyncSession, owner_id: str, search_id: str) -> int:
    """``search.run``: a new or changed search, over what's already here."""
    search = await repo.search(session, owner_id, search_id)
    return await match_opportunities(
        session, owner_id, await repo.opportunities_of(session, owner_id, search.pack), searches=[search]
    )
