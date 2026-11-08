"""
Sources: public listings APIs, fetched on a schedule (logic/scheduler.py) or when asked.

A fetch upserts each posting as an opportunity:

- the same link again is the same opportunity, refreshed unless the person has edited it;
- the same job from another source (same issuer, title and place) is that opportunity too, not a second one;
- a posting the source no longer lists is closed.

Then the owner's searches run over what's new or changed, and what passes becomes a match to be scored.
"""

import hashlib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument
from apply.libs.extract import FetchError, canonical_url
from apply.libs.jobs import JobContext
from apply.packs import get_pack
from apply.packs.base import Listing, SourceAdapter
from apply.runtime import Runtime
from apply.store.sql.models import Opportunity, Source
from apply.store.sql.repo import discovery as repo
from apply.store.sql.repo import opportunities as opportunities_repo

from . import background, searches

logger = logging.getLogger("apply.logic.sources")


def recognise(pack: str, url: str) -> tuple[str, dict[str, str]]:
    """Which kind of source a pasted address is (a company's job board), and its config. 422 if none knows it."""
    for adapter in get_pack(pack).sources:
        if (config := adapter.recognise(url)) is not None:
            return adapter.kind, adapter.validate_config(config)
    raise InvalidArgument(ErrorCode.SOURCE_NOT_RECOGNISED, "no source knows that address")


def adapter_of(source: Source) -> SourceAdapter:
    return get_pack(source.pack).source(source.kind)


def due(source: Source, now: datetime) -> bool:
    interval = max(source.interval_hours, adapter_of(source).min_interval_hours)
    return source.last_fetched_at is None or source.last_fetched_at + timedelta(hours=interval) <= now


# ── reading and changing sources ─────────────────────────────────────────────


async def create(
    session: AsyncSession,
    owner_id: str,
    *,
    pack: str,
    kind: str,
    config: dict[str, Any],
    name: str | None,
    interval_hours: float,
    enabled: bool,
) -> Source:
    adapter = get_pack(pack).source(kind)
    clean = adapter.validate_config(config)
    source = Source(
        owner_id=owner_id,
        pack=pack,
        kind=kind,
        config=clean,
        name=(name or adapter.display_name(clean))[:200],
        interval_hours=max(interval_hours, adapter.min_interval_hours),
        enabled=enabled,
    )
    session.add(source)
    await session.flush()
    if enabled:
        await background.fetch_source(session, owner_id, source.id, interactive=True)
    return source


async def update(session: AsyncSession, owner_id: str, source_id: str, changes: dict[str, Any]) -> Source:
    source = await repo.source(session, owner_id, source_id, for_update=True)
    adapter = adapter_of(source)
    if changes.get("config") is not None:
        source.config = adapter.validate_config(changes["config"])
    if changes.get("name"):
        source.name = changes["name"][:200]
    if changes.get("interval_hours") is not None:
        source.interval_hours = max(float(changes["interval_hours"]), adapter.min_interval_hours)
    if changes.get("enabled") is not None:
        source.enabled = bool(changes["enabled"])
    await session.flush()
    return source


async def delete(session: AsyncSession, owner_id: str, source_id: str) -> None:
    await session.delete(await repo.source(session, owner_id, source_id, for_update=True))


async def fetch_now(session: AsyncSession, owner_id: str, source_id: str) -> Source:
    """Queue a fetch now, unless the source's terms say it's too soon."""
    source = await repo.source(session, owner_id, source_id)
    adapter = adapter_of(source)
    now = datetime.now(UTC)
    if source.last_fetched_at and source.last_fetched_at + timedelta(hours=adapter.min_interval_hours) > now:
        wait = source.last_fetched_at + timedelta(hours=adapter.min_interval_hours) - now
        raise Conflict(
            ErrorCode.SOURCE_TOO_SOON,
            f"{adapter.kind} asks for at least {adapter.min_interval_hours} h between requests",
            extra={"retry_after": int(wait.total_seconds()) + 1},
        )
    await background.fetch_source(session, owner_id, source.id, interactive=True)
    return source


async def list_(session: AsyncSession, owner_id: str, pack: str | None) -> Sequence[Source]:
    return await repo.sources(session, owner_id, pack)


async def get(session: AsyncSession, owner_id: str, source_id: str) -> Source:
    return await repo.source(session, owner_id, source_id)


# ── the fetch ────────────────────────────────────────────────────────────────


async def fetch(rt: Runtime, ctx: JobContext) -> None:
    """``source.fetch``: list a source's postings, upsert them, close the gone ones, match what's new."""
    source_id = ctx.payload["source_id"]
    async with rt.db.transaction() as session:
        source = await repo.source_any_owner(session, source_id)
        if source is None or not source.enabled:
            return
        adapter = adapter_of(source)
        config, kind, owner_id = dict(source.config), source.kind, source.owner_id

    base_url = rt.settings.source_base_urls.get(kind, adapter.default_base_url).rstrip("/")
    try:
        listings = await adapter.fetch(rt.fetcher, config, base_url)
        error: str | None = None
    except FetchError as exc:
        logger.warning("sources: %s (%s) failed: %s", kind, source_id, exc)
        listings, error = [], exc.code
    except (KeyError, TypeError, ValueError, AttributeError) as exc:  # an answer not in the shape the API documents
        logger.warning("sources: %s (%s) answered something unexpected: %r", kind, source_id, exc)
        listings, error = [], ErrorCode.SOURCE_FAILED.value

    async with rt.db.transaction() as session:
        source = await repo.source_any_owner(session, source_id, for_update=True)
        if source is None:
            return
        source.last_fetched_at = datetime.now(UTC)
        if error:
            source.last_status, source.last_error_code = "failed", error
            return
        changed, seen = await upsert_listings(session, source, listings)
        await repo.close_unlisted(session, source.id, seen)
        source.last_status, source.last_error_code, source.last_count = "ok", None, len(listings)
        await searches.match_opportunities(session, owner_id, changed)


async def upsert_listings(
    session: AsyncSession, source: Source, listings: list[Listing]
) -> tuple[list[Opportunity], set[str]]:
    """Returns the opportunities that are new or changed (to match), and the ids of all listed now."""
    pack = get_pack(source.pack)
    changed: list[Opportunity] = []
    seen: set[str] = set()
    now = datetime.now(UTC)
    for listing in listings:
        try:
            attributes = pack.validate_opportunity(listing.attributes)
        except Exception:  # noqa: BLE001 - one odd posting mustn't stop the rest; it's logged and skipped
            logger.warning("sources: skipped a posting from %s that doesn't fit the pack", source.kind)
            continue
        ref = canonical_url(listing.source_url)
        key = pack.dedupe_key(listing.issuer_name, listing.title, attributes)
        content_hash = hashlib.sha256(repr(sorted(attributes.items())).encode()).hexdigest()
        opp = await opportunities_repo.by_ref(session, source.owner_id, ref)
        if opp is None:
            opp = await repo.opportunity_by_dedupe(session, source.owner_id, key)
            if opp is not None:  # the same job, found first on another source
                opp.last_seen_at = now
                seen.add(opp.id)
                continue
            opp = Opportunity(
                owner_id=source.owner_id,
                pack=source.pack,
                title=listing.title[:500],
                issuer_name=listing.issuer_name[:300],
                source_url=listing.source_url,
                apply_url=listing.apply_url,
                deadline=listing.deadline,
                status="open",
                attributes=attributes,
                external_ref=ref[:2100],
                content_hash=content_hash,
                source_text=listing.source_text,
                extraction={"status": "ready", "method": "source", "error_code": None},
                source_id=source.id,
                dedupe_key=key,
                posted_at=listing.posted_at,
            )
            session.add(opp)
            await session.flush()
            changed.append(opp)
        else:
            if opp.content_hash != content_hash and not opp.extraction.get("edited"):
                opp.attributes = attributes
                opp.title, opp.issuer_name = listing.title[:500], listing.issuer_name[:300]
                opp.content_hash = content_hash
                changed.append(opp)
            if opp.status == "closed":
                opp.status = "open"
                changed.append(opp)
            opp.last_seen_at = now
            opp.source_id = opp.source_id or source.id
            opp.dedupe_key = opp.dedupe_key or key
        seen.add(opp.id)
    await session.flush()
    return changed, seen
