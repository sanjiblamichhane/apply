"""
Reviewing a written document before it goes out: edit it (a new version, checked again), decide on each
warning (removed, or "It's true"), mark the version reviewed. And its PDF, rendered in the worker.
"""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, NotFound
from apply.libs import storage
from apply.libs.jobs import JobContext
from apply.libs.render import Kind, render_html, render_pdf, render_word
from apply.packs import get_pack
from apply.packs.base import ProfileInput
from apply.runtime import Runtime
from apply.store.sql.models import ApplicationDocument, RenderedFile
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import documents as documents_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo
from apply.store.sql.repo import review as repo

from . import background, files, templates

logger = logging.getLogger("apply.logic.review")


def content_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode()).hexdigest()


def rendered_hash(markdown: str, template: str) -> str:
    """What a version's files are made from: its words and the template (a new template makes them again)."""
    return content_hash(f"{content_hash(template)}\n{markdown}")


async def layout_of(session: AsyncSession, doc: ApplicationDocument) -> Kind:
    """Which template a document is made in: its type's (a letter's, or a resume's)."""
    application = await applications_repo.get_any_owner(session, doc.application_id)
    opp = await opportunities_repo.get(session, doc.owner_id, application.opportunity_id)  # type: ignore[union-attr]
    return get_pack(opp.pack).document_type(doc.document_type).layout


async def digest_of(session: AsyncSession, doc: ApplicationDocument) -> str:
    template = await templates.template(session, doc.owner_id, await layout_of(session, doc))
    return rendered_hash(doc.content_markdown, template)


KINDS = {"pdf": files.PDF, "html": files.HTML, "docx": files.DOCX}


async def _ready(
    session: AsyncSession, owner_id: str, application_id: str, document_id: str, *, for_update: bool = False
) -> ApplicationDocument:
    doc = await documents_repo.get(session, owner_id, application_id, document_id)
    if for_update:
        await session.refresh(doc, with_for_update=True)
    if doc.status != "ready":
        raise Conflict(ErrorCode.DOCUMENT_NOT_READY, "That document isn't written yet")
    return doc


async def after_written(session: AsyncSession, document: ApplicationDocument) -> None:
    """A new ready version: check its claims and make its PDF."""
    document.claims_status = "pending"
    await background.check_document(session, document.owner_id, document.id)
    await background.render_document(session, document.owner_id, document.id)


async def edit(
    session: AsyncSession, owner_id: str, application_id: str, document_id: str, content: str
) -> ApplicationDocument:
    """The person's own wording: a new version (the one in use), checked again; the old one is kept."""
    base = await _ready(session, owner_id, application_id, document_id)
    await applications_repo.get(session, owner_id, application_id, for_update=True)  # versions one at a time
    version = await documents_repo.last_version(session, application_id, base.document_type) + 1
    await documents_repo.deactivate(session, application_id, base.document_type)
    await session.flush()
    edited = await documents_repo.add(
        session,
        owner_id=owner_id,
        application_id=application_id,
        profile_id=base.profile_id,
        document_type=base.document_type,
        status="ready",
        version=version,
        is_active=True,
        content_markdown=content.strip(),
        source="edited",
        model=base.model,
        finished_at=datetime.now(UTC),
        # "It's true" carries over (the check keeps it for the same words); a correction was for the old wording.
        claim_warnings=[w for w in base.claim_warnings if w.get("resolved") == "kept"],
        revision=carried(base),
    )
    await after_written(session, edited)
    return edited


def carried(base: ApplicationDocument) -> dict | None:
    """The corrections a version was written with, for the next: a fact the person gave once stays given."""
    corrections = (base.revision or {}).get("corrections") or []
    return {"corrections": corrections} if corrections else None


async def resolve(
    session: AsyncSession,
    owner_id: str,
    application_id: str,
    document_id: str,
    warning_id: str,
    resolution: str,
    correction: str = "",
) -> ApplicationDocument:
    """ "It's true" (kept), "It's wrong" with what's true instead (empty: take it out), or open again."""
    doc = await _ready(session, owner_id, application_id, document_id, for_update=True)
    warnings = list(doc.claim_warnings or [])
    for i, warning in enumerate(warnings):
        if warning.get("id") == warning_id:
            decided = {k: v for k, v in warning.items() if k != "correction"}
            decided["resolved"] = resolution if resolution in ("kept", "wrong") else None
            if resolution == "wrong":
                decided["correction"] = correction.strip()
            warnings[i] = decided
            doc.claim_warnings = warnings
            await session.flush()
            return doc
    raise NotFound(ErrorCode.WARNING_NOT_FOUND, "No such warning on this version")


async def mark_reviewed(
    session: AsyncSession, owner_id: str, application_id: str, document_id: str, reviewed: bool
) -> ApplicationDocument:
    doc = await _ready(session, owner_id, application_id, document_id, for_update=True)
    doc.reviewed_at = datetime.now(UTC) if reviewed else None
    await session.flush()
    return doc


async def check_again(
    session: AsyncSession, owner_id: str, application_id: str, document_id: str
) -> ApplicationDocument:
    doc = await _ready(session, owner_id, application_id, document_id, for_update=True)
    doc.claims_status = "pending"
    await background.check_document(session, owner_id, doc.id)
    await session.flush()
    return doc


# ── files: the page and the PDF ─────────────────────────────────────────────────────────────────────


async def render(rt: Runtime, ctx: JobContext) -> None:
    """
    ``document.render``: the version in the template, as its page (HTML) and as a tagged PDF, and as a Word file
    to edit, kept by content, so an unchanged version isn't redone.
    """
    document_id = ctx.payload["document_id"]
    async with rt.db.transaction() as session:
        doc = await documents_repo.get_any_owner(session, document_id)
        if doc is None or doc.status != "ready":
            return
        application = await applications_repo.get_any_owner(session, doc.application_id)
        opp = await opportunities_repo.get(session, doc.owner_id, application.opportunity_id)  # type: ignore[union-attr]
        pack = get_pack(opp.pack)
        spec = pack.document_type(doc.document_type)
        template = await templates.template(session, doc.owner_id, spec.layout)
        digest = rendered_hash(doc.content_markdown, template)
        missing = [k for k in KINDS if await repo.rendered(session, doc.id, k, digest) is None]
        if not missing:
            return
        profile = await profiles_repo.default_for(session, doc.owner_id, opp.pack) if doc.profile_id is None else None
        if doc.profile_id:
            try:
                profile = await profiles_repo.get(session, doc.owner_id, doc.profile_id)
            except NotFound:
                profile = None
        author = (
            pack.person_name(ProfileInput(name=profile.name, summary=profile.summary, attributes=profile.attributes))
            if profile
            else ""
        )
        label = spec.label["en"]
        # The template's own: "Sam Rai - Resume", "Sam Rai - Cover Letter".
        title = f"{author} - {label.title()}" if author else label.title()
        whom = f" from {author}" if author else ""
        description = (
            f"{label}{whom} for {opp.title}" + (f" at {opp.issuer_name}" if opp.issuer_name else "") + "."
            if spec.layout == "letter" and opp.title
            else f"{label}{whom}."
        )
        markdown, owner_id, layout = doc.content_markdown, doc.owner_id, spec.layout

    # One page, and the PDF is that page printed: what's previewed is what's downloaded.
    page = render_html(markdown, kind=layout, template=template, title=title, description=description, lang="en")
    made: dict[str, bytes] = {}
    if "html" in missing:
        made["html"] = page
    if "pdf" in missing:
        made["pdf"] = await asyncio.to_thread(render_pdf, page, paper=rt.settings.pdf_paper)
    if "docx" in missing:
        made["docx"] = render_word(
            markdown, kind=layout, title=title, description=description, lang="en", paper=rt.settings.pdf_paper
        )
    for kind, data in made.items():
        key = storage.document_file(owner_id, document_id, digest, kind)
        await files.put(rt, key, data, KINDS[kind])  # the file first: a saved row always has its file
    async with rt.db.transaction() as session:
        for kind, data in made.items():
            if await repo.rendered(session, document_id, kind, digest) is None:
                session.add(
                    RenderedFile(
                        owner_id=owner_id,
                        document_id=document_id,
                        kind=kind,
                        sha256=digest,
                        size=len(data),
                        object_key=storage.document_file(owner_id, document_id, digest, kind),
                    )
                )


async def rendered(
    session: AsyncSession, owner_id: str, application_id: str, document_id: str, kind: str = "pdf"
) -> RenderedFile | None:
    """
    The version as a file (``pdf``, ``html``), or None with its making queued: the caller says RENDER_PENDING
    once this transaction is committed (raised in it, the queued job would go with it).
    """
    doc = await _ready(session, owner_id, application_id, document_id)
    found = await repo.rendered(session, doc.id, kind, await digest_of(session, doc))
    if found is None:
        await background.render_document(session, owner_id, doc.id)
    return found


def pending() -> Conflict:
    return Conflict(
        ErrorCode.RENDER_PENDING,
        "The file is being made; ask again in a moment",
        extra={"retry_after": 1},
        headers={"Retry-After": "1"},
    )
