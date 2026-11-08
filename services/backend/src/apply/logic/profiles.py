"""
Profiles: who is applying. Attributes are held to the pack's profile fields; one profile per pack is the default.

A profile can be made from an uploaded document (a resume, a capability statement): it's saved at once with the
file (in the bucket) and its text, and the model reads the text into the pack's fields in the background
(``profile.read``); ``reading.status`` is ``pending`` meanwhile. The person's own edits win: a profile edited while
it's being read isn't overwritten (``stopped``). The model fills in only what the document says (packs/base.py).
"""

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument
from apply.libs import storage
from apply.libs.extract import DocumentError, document_text
from apply.libs.extract.document import CONTENT_TYPES, EXTENSIONS
from apply.libs.jobs import JobContext
from apply.libs.llm import LLMError
from apply.packs import get_pack
from apply.packs.base import ProfileInput
from apply.runtime import Runtime
from apply.store.sql.db import new_id
from apply.store.sql.models import Profile
from apply.store.sql.repo import profiles as repo

from . import background, files

logger = logging.getLogger("apply.logic.profiles")

PENDING, READY, FAILED, STOPPED = "pending", "ready", "failed", "stopped"
CONTENT_FIELDS = ("name", "summary", "attributes", "tone_instructions")


async def create(
    session: AsyncSession,
    owner_id: str,
    *,
    pack: str,
    kind: str,
    name: str,
    summary: str,
    attributes: dict[str, Any],
    tone_instructions: str,
    is_default: bool | None,
    **made_from: Any,  # id, source, source_text, reading: a profile made from a document
) -> Profile:
    spec = get_pack(pack)
    if kind not in spec.profile_kinds:
        raise InvalidArgument(
            ErrorCode.VALIDATION_FAILED,
            f"The {pack} pack takes profiles of kind {', '.join(spec.profile_kinds)}, not {kind}",
        )
    attributes = spec.validate_profile(attributes)
    first = await repo.count(session, owner_id, pack) == 0
    make_default = first if is_default is None else (is_default or first)
    if make_default:
        await repo.clear_default(session, owner_id, pack)
    return await repo.add(
        session,
        owner_id=owner_id,
        pack=pack,
        kind=kind,
        name=name,
        summary=summary,
        attributes=attributes,
        tone_instructions=tone_instructions,
        is_default=make_default,
        **made_from,
    )


async def update(session: AsyncSession, owner_id: str, profile_id: str, changes: dict[str, Any]) -> Profile:
    profile = await repo.get(session, owner_id, profile_id, for_update=True)
    spec = get_pack(profile.pack)
    if profile.reading and any(k in changes for k in CONTENT_FIELDS):
        if profile.reading.get("status") == PENDING:
            profile.reading = {"status": STOPPED, "error_code": None}  # the person's edits win over the reading
        else:
            profile.reading = {**profile.reading, "edited": True}  # checked and saved by the person
    if "attributes" in changes:
        profile.attributes = spec.validate_profile(changes["attributes"])
    for key in ("name", "summary", "tone_instructions"):
        if key in changes:
            setattr(profile, key, changes[key])
    if changes.get("is_default") is True and not profile.is_default:
        await repo.clear_default(session, owner_id, profile.pack)
        profile.is_default = True
    elif changes.get("is_default") is False and profile.is_default:
        # Another profile takes over as the default, if there is one.
        other = await repo.newest_other(session, owner_id, profile.pack, profile.id)
        if other is not None:
            profile.is_default = False
            await session.flush()
            other.is_default = True
    await session.flush()
    return profile


async def delete(session: AsyncSession, owner_id: str, profile_id: str) -> str | None:
    """The profile goes; returns its document's key in the bucket (to remove once this is saved), if it has one."""
    profile = await repo.get(session, owner_id, profile_id, for_update=True)
    was_default, pack, source_key = profile.is_default, profile.pack, profile.source.get("key")
    await session.delete(profile)
    await session.flush()
    if was_default:
        other = await repo.newest_other(session, owner_id, pack, profile_id)
        if other is not None:
            other.is_default = True
            await session.flush()
    return source_key


async def duplicate(session: AsyncSession, owner_id: str, profile_id: str, *, name: str | None) -> Profile:
    """A copy to change what's different: the same fields as "Name (copy)", not the default, without the document."""
    original = await repo.get(session, owner_id, profile_id)
    return await create(
        session,
        owner_id,
        pack=original.pack,
        kind=original.kind,
        name=name or f"{original.name[:193]} (copy)",
        summary=original.summary,
        attributes=dict(original.attributes),
        tone_instructions=original.tone_instructions,
        is_default=False,
    )


# ── made from a document ─────────────────────────────────────────────────────


def _name_from(filename: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    return " ".join(re.sub(r"[_\s]+", " ", stem).split())[:200] or "Profile"


def _safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^\w .()-]", "", base, flags=re.UNICODE).strip()[:200] or "document"


async def import_document(
    rt: Runtime,
    owner_id: str,
    *,
    pack: str,
    data: bytes,
    filename: str,
    name: str | None = None,
    kind: str | None = None,
    is_default: bool | None = None,
) -> Profile:
    """A profile from an uploaded document: saved now with the file and its text, read by the model next."""
    spec = get_pack(pack)
    if len(data) > rt.settings.upload_max_bytes:
        raise InvalidArgument(
            ErrorCode.UPLOAD_TOO_LARGE, "The file is too large", extra={"max_bytes": rt.settings.upload_max_bytes}
        )
    try:
        found = await asyncio.to_thread(document_text, data)
    except DocumentError as exc:
        code = ErrorCode.UPLOAD_NO_TEXT if exc.reason == "no_text" else ErrorCode.UPLOAD_UNSUPPORTED
        raise InvalidArgument(code, str(exc)) from exc
    profile_id = new_id()
    key = storage.profile_source(owner_id, profile_id, EXTENSIONS[found.kind])
    await files.put(rt, key, data, CONTENT_TYPES[found.kind])  # the file first: a saved profile has its file
    async with rt.db.transaction() as session:
        profile = await create(
            session,
            owner_id,
            pack=pack,
            kind=kind or spec.profile_kinds[0],
            name=(name or "").strip() or _name_from(filename),
            summary="",
            attributes={},
            tone_instructions="",
            is_default=is_default,
            id=profile_id,
            source={"key": key, "name": _safe_filename(filename), "kind": found.kind, "size": len(data)},
            source_text=found.text,
            reading={"status": PENDING, "error_code": None},
        )
        await background.read_profile(session, owner_id, profile.id)
    return profile


async def read(rt: Runtime, ctx: JobContext) -> None:
    """``profile.read``: the model reads the kept text into the pack's profile fields."""
    profile_id = ctx.payload["profile_id"]
    async with rt.db.transaction() as session:
        profile = await repo.get_any_owner(session, profile_id)
        if profile is None or profile.reading.get("status") != PENDING:
            return  # deleted, edited by the person, or already read
        spec = get_pack(profile.pack)
        prompt = spec.reading_prompt(profile.source_text)

    error: str | None = None
    summary, attributes = "", {}
    try:
        data = await rt.model.complete_json(prompt.text, spec.reading_schema(), purpose=prompt.purpose)
        summary, attributes = spec.from_reading(data)
        if not summary and attributes == spec.validate_profile({}):
            error = ErrorCode.EXTRACT_FAILED.value  # nothing read: left for the person, not filled with guesses
    except LLMError as exc:
        logger.warning("profiles: the model could not read %s: %s", profile_id, exc)
        error = exc.code

    async with rt.db.transaction() as session:
        profile = await repo.get_any_owner(session, profile_id, for_update=True)
        if profile is None or profile.reading.get("status") != PENDING:
            return
        if error is None:
            profile.summary, profile.attributes = summary, attributes
            person = spec.person_name(ProfileInput(name=profile.name, summary=summary, attributes=attributes))
            if person:
                profile.name = person[:200]
        profile.reading = {"status": FAILED if error else READY, "error_code": error}


async def give_up_reading(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        profile = await repo.get_any_owner(session, ctx.payload["profile_id"], for_update=True)
        if profile is not None and profile.reading.get("status") == PENDING:
            profile.reading = {"status": FAILED, "error_code": ErrorCode.EXTRACT_FAILED.value}


async def read_again(session: AsyncSession, owner_id: str, profile_id: str) -> Profile:
    """Read the kept document again (after the model failed, say). What's read replaces the profile's fields."""
    profile = await repo.get(session, owner_id, profile_id, for_update=True)
    if not profile.source_text:
        raise Conflict(ErrorCode.PROFILE_NOT_READ, "This profile wasn't made from a document")
    if profile.reading.get("status") != PENDING:
        profile.reading = {"status": PENDING, "error_code": None}
        await background.read_profile(session, owner_id, profile.id)
        await session.flush()
    return profile


async def source(rt: Runtime, session: AsyncSession, owner_id: str, profile_id: str) -> tuple[dict[str, Any], bytes]:
    """The document a profile was made from: (its details, its bytes)."""
    profile = await repo.get(session, owner_id, profile_id)
    key = profile.source.get("key")
    data = await files.get_key(rt, key) if key else None
    if data is None:
        raise Conflict(ErrorCode.PROFILE_NOT_READ, "This profile wasn't made from a document")
    return profile.source, data


async def get(session: AsyncSession, owner_id: str, profile_id: str) -> Profile:
    return await repo.get(session, owner_id, profile_id)


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, after: str | None, limit: int
) -> tuple[Sequence[Profile], str | None]:
    return await repo.list_(session, owner_id, pack=pack, after=after, limit=limit)
