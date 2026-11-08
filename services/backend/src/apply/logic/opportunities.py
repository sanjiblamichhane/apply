"""
Opportunities: pasted as a link or as text, read, and corrected by the person.

1. A link is fetched safely (libs/extract). If the page carries the pack's JSON-LD (the job pack's ``JobPosting``), the
   opportunity is filled in at once.
2. Otherwise (or for pasted text) the text is kept and the model reads it in the background
   (``opportunity.extract``); the opportunity's ``extraction.status`` is ``pending`` meanwhile.
3. A page that can't be read (blocked, a sign-in wall, not a web page) or a model that fails leaves
   ``extraction.status`` ``manual`` with a code: the fields stay empty for the person, never filled with guesses.
4. The same link (canonical form) or the same text again is the same opportunity.
5. The browser extension sends the page as the person's browser shows it along with its link, so nothing is
   fetched again (and a page drawn by scripts, like board03's, can still be read).

Editing the fields takes the opportunity over from the extractor: a model reply arriving later changes nothing.
"""

import hashlib
import logging
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, InvalidArgument
from apply.libs.extract import (
    FetchError,
    Page,
    canonical_url,
    check_url,
    find_nodes,
    looks_like_a_wall,
    page_text,
    title,
)
from apply.libs.jobs import JobContext
from apply.libs.llm import LLMError
from apply.packs import Pack, get_pack
from apply.runtime import Runtime
from apply.store.sql.models import Opportunity
from apply.store.sql.repo import opportunities as repo

from . import background

logger = logging.getLogger("apply.logic.opportunities")

MAX_TEXT = 100_000  # characters someone may paste
MODEL_TEXT = 40_000  # characters given to the model (fits num_ctx 16384 with the prompt)
MIN_PAGE_TEXT = 300  # less than this is a wall, a script-only page or an error page
REFUSED = {FetchError.URL_NOT_ALLOWED, FetchError.ADDRESS_NOT_ALLOWED}

PENDING, READY, MANUAL = "pending", "ready", "manual"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _normalise(text: str) -> str:
    return "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())


async def paste(
    rt: Runtime, owner_id: str, *, pack_key: str, url: str | None, text: str | None, html: str | None = None
) -> tuple[Opportunity, bool]:
    """Returns the opportunity and whether it is new. ``html``: the page at ``url`` as the browser has it."""
    pack = get_pack(pack_key)
    url = (url or "").strip() or None
    text = (text or "").strip() or None
    if (url is None) == (text is None):
        raise InvalidArgument(ErrorCode.URL_OR_TEXT_REQUIRED, "Paste a link or the text, one of the two")
    if url is not None:
        return await _paste_url(rt, owner_id, pack, url, html=html)
    assert text is not None
    if len(text) > MAX_TEXT:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"That is more than {MAX_TEXT} characters")
    return await _paste_text(rt, owner_id, pack, text)


async def _existing(rt: Runtime, owner_id: str, ref: str) -> Opportunity | None:
    async with rt.db.transaction() as session:
        found = await repo.by_ref(session, owner_id, ref)
        if found is not None:
            await repo.seen_again(session, found)
        return found


async def _save(rt: Runtime, owner_id: str, values: dict[str, Any], *, extract: bool) -> tuple[Opportunity, bool]:
    async with rt.db.transaction() as session:
        new_id = await repo.insert_new(session, {"owner_id": owner_id, **values})
        if new_id is None:  # someone pasted the same thing a moment ago
            found = await repo.by_ref(session, owner_id, values["external_ref"])
            assert found is not None
            await repo.seen_again(session, found)
            return found, False
        if extract:
            await background.extract_opportunity(session, owner_id, new_id)
        return await repo.get(session, owner_id, new_id), True


async def _paste_text(rt: Runtime, owner_id: str, pack: Pack, text: str) -> tuple[Opportunity, bool]:
    normalised = _normalise(text)
    ref = f"text:{_sha(pack.key + chr(0) + normalised)}"
    found = await _existing(rt, owner_id, ref)
    if found is not None:
        return found, False
    first_line = normalised.splitlines()[0][:500] if normalised else ""
    return await _save(
        rt,
        owner_id,
        {
            "pack": pack.key,
            "title": first_line,
            "external_ref": ref,
            "content_hash": _sha(normalised),
            "source_text": text,
            "extraction": {"status": PENDING, "method": "model", "error_code": None},
        },
        extract=True,
    )


async def _paste_url(
    rt: Runtime, owner_id: str, pack: Pack, url: str, *, html: str | None = None
) -> tuple[Opportunity, bool]:
    try:
        check_url(url)
    except FetchError as exc:
        raise InvalidArgument(ErrorCode(exc.code), str(exc)) from exc
    ref = canonical_url(url)
    found = await _existing(rt, owner_id, ref)
    if found is not None:
        return found, False

    base: dict[str, Any] = {"pack": pack.key, "source_url": ref, "apply_url": url, "external_ref": ref}
    try:
        page = Page(url=url, status=200, content_type="text/html", html=html) if html else await rt.fetcher.fetch(url)
    except FetchError as exc:
        if exc.code in REFUSED:
            raise InvalidArgument(ErrorCode(exc.code), str(exc)) from exc
        logger.info("opportunities: could not fetch %s: %s", ref, exc)
        return await _save(
            rt,
            owner_id,
            base
            | {
                "content_hash": _sha(ref),
                "extraction": {"status": MANUAL, "method": "manual", "error_code": exc.code},
            },
            extract=False,
        )

    for node in find_nodes(page.html, set(pack.json_ld_types)):
        extracted = pack.from_json_ld(node, page.url)
        if extracted is not None:
            return await _save(
                rt,
                owner_id,
                base
                | {
                    "title": extracted.title,
                    "issuer_name": extracted.issuer_name,
                    "attributes": pack.validate_opportunity(extracted.attributes),
                    "apply_url": extracted.apply_url or url,
                    "deadline": extracted.deadline,
                    "status": extracted.status,
                    "content_hash": _sha(page.html),
                    "source_text": page_text(page.html, limit=MODEL_TEXT),
                    "extraction": {"status": READY, "method": "json_ld", "error_code": None},
                },
                extract=False,
            )

    text = page_text(page.html, limit=MODEL_TEXT)
    if len(text) < MIN_PAGE_TEXT or looks_like_a_wall(text):
        code = FetchError.BLOCKED if looks_like_a_wall(text) else ErrorCode.FETCH_TOO_LITTLE_TEXT.value
        return await _save(
            rt,
            owner_id,
            base
            | {
                "title": title(page.html),
                "content_hash": _sha(page.html),
                "source_text": text,
                "extraction": {"status": MANUAL, "method": "manual", "error_code": code},
            },
            extract=False,
        )
    return await _save(
        rt,
        owner_id,
        base
        | {
            "title": title(page.html),
            "content_hash": _sha(page.html),
            "source_text": text,
            "extraction": {"status": PENDING, "method": "model", "error_code": None},
        },
        extract=True,
    )


# ── the background job ───────────────────────────────────────────────────────


async def extract_with_model(rt: Runtime, ctx: JobContext) -> None:
    """``opportunity.extract``: the model reads the kept text into the pack's fields."""
    opportunity_id = ctx.payload["opportunity_id"]
    async with rt.db.transaction() as session:
        opp = await repo.get_any_owner(session, opportunity_id)
        if opp is None or opp.extraction.get("status") != PENDING:
            return  # deleted, edited by the person, or already done
        pack = get_pack(opp.pack)
        prompt = pack.extraction_prompt(opp.source_text[:MODEL_TEXT])

    try:
        data = await rt.model.complete_json(prompt.text, pack.extraction_schema(), purpose=prompt.purpose)
        extracted = pack.from_extraction(data)
        error: str | None = None if extracted.title else ErrorCode.EXTRACT_FAILED.value
    except LLMError as exc:
        logger.warning("opportunities: the model could not read %s: %s", opportunity_id, exc)
        extracted, error = None, exc.code

    async with rt.db.transaction() as session:
        opp = await repo.get_any_owner(session, opportunity_id, for_update=True)
        if opp is None or opp.extraction.get("status") != PENDING:
            return
        if extracted is not None:
            opp.attributes = pack.validate_opportunity(extracted.attributes)
            opp.title = extracted.title or opp.title
            opp.issuer_name = extracted.issuer_name or opp.issuer_name
        opp.extraction = {"status": MANUAL if error else READY, "method": "model", "error_code": error}


async def give_up_extraction(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        opp = await repo.get_any_owner(session, ctx.payload["opportunity_id"], for_update=True)
        if opp is not None and opp.extraction.get("status") == PENDING:
            opp.extraction = {"status": MANUAL, "method": "model", "error_code": ErrorCode.EXTRACT_FAILED.value}


# ── reading and correcting ───────────────────────────────────────────────────


async def update(session: AsyncSession, owner_id: str, opportunity_id: str, changes: dict[str, Any]) -> Opportunity:
    opp = await repo.get(session, owner_id, opportunity_id, for_update=True)
    pack = get_pack(opp.pack)
    if "attributes" in changes:
        merged = {**opp.attributes, **changes["attributes"]}
        opp.attributes = pack.validate_opportunity(merged)
        derived_title, derived_issuer = pack.describe(opp.attributes)
        opp.title = changes.get("title") or derived_title or opp.title
        opp.issuer_name = changes.get("issuer_name") or derived_issuer or opp.issuer_name
    for key in ("title", "issuer_name", "apply_url", "deadline", "status"):
        if key in changes and changes[key] is not None:
            setattr(opp, key, changes[key])
    if opp.extraction.get("status") == PENDING:
        opp.extraction = {"status": MANUAL, "method": "manual", "error_code": None}
    elif changes:
        opp.extraction = {**opp.extraction, "edited": True}
    await session.flush()
    return opp


async def extract_again(rt: Runtime, owner_id: str, opportunity_id: str) -> Opportunity:
    """Ask the model to read it again (after it failed, or after the person cleared the fields)."""
    async with rt.db.transaction() as session:
        opp = await repo.get(session, owner_id, opportunity_id, for_update=True)
        if opp.extraction.get("status") == PENDING:
            return opp
        if not opp.source_text.strip():
            raise InvalidArgument(ErrorCode.FETCH_TOO_LITTLE_TEXT, "There is no text to read; fill in the fields")
        opp.extraction = {"status": PENDING, "method": "model", "error_code": None}
        await background.extract_opportunity(session, owner_id, opp.id)
        await session.flush()
        return opp


async def get(session: AsyncSession, owner_id: str, opportunity_id: str) -> Opportunity:
    return await repo.get(session, owner_id, opportunity_id)


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, after: str | None, limit: int
) -> tuple[Sequence[Opportunity], str | None]:
    return await repo.list_(session, owner_id, pack=pack, after=after, limit=limit)
