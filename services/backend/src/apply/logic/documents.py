"""
Documents for an application, written by the model in the background.

What matters is what people see while it works:

- the version they are using stays in use until a new one is finished;
- a document being written, or one that failed, is never shown as a version (version 0, inactive);
- a failure always ends as ``failed`` with a code, never "pending" for ever (the job's give-up hook covers a
  worker that dies);
- asking again while one is being written returns that one rather than queuing a second;
- running the job twice writes one version.

There is no fallback template: a document the model didn't write is a failed document, not a made-up one.
"""

import logging
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, InvalidArgument, NotFound
from apply.libs.jobs import JobContext
from apply.libs.llm import LLMError
from apply.libs.render import with_letterhead
from apply.packs import get_pack
from apply.packs.base import OpportunityInput, ProfileInput
from apply.runtime import Runtime
from apply.store.sql.models import ApplicationDocument
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import documents as repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo

from . import background, review

logger = logging.getLogger("apply.logic.documents")

PENDING, READY, FAILED = "pending", "ready", "failed"
_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)


async def request(
    session: AsyncSession, owner_id: str, application_id: str, *, document_type: str, profile_id: str | None
) -> tuple[ApplicationDocument, bool]:
    """Ask for a document to be written. Returns it (pending) and whether a new one was queued."""
    application = await applications_repo.get(session, owner_id, application_id, for_update=True)
    opportunity = await opportunities_repo.get(session, owner_id, application.opportunity_id)
    spec = get_pack(opportunity.pack).document_type(document_type)
    if not spec.generatable:
        raise InvalidArgument(ErrorCode.DOCUMENT_TYPE_NOT_GENERATABLE, f"{document_type} is not written by the model")

    profile_id = profile_id or application.profile_id
    if profile_id is None:
        default = await profiles_repo.default_for(session, owner_id, opportunity.pack)
        profile_id = default.id if default else None
    if profile_id is None:
        raise InvalidArgument(ErrorCode.PROFILE_REQUIRED, "Add a profile first: the document is written from it")
    profile = await profiles_repo.get(session, owner_id, profile_id)
    if profile.pack != opportunity.pack:
        raise InvalidArgument(ErrorCode.PROFILE_PACK_MISMATCH, "That profile is for another pack")

    waiting = await repo.pending(session, application.id, document_type)
    if waiting is not None:
        return waiting, False
    try:
        async with session.begin_nested():
            document = await repo.add(
                session,
                owner_id=owner_id,
                application_id=application.id,
                profile_id=profile.id,
                document_type=document_type,
                status=PENDING,
                version=0,
                is_active=False,
                source="generated",
            )
    except IntegrityError:
        waiting = await repo.pending(session, application.id, document_type)
        if waiting is None:
            raise
        return waiting, False
    await background.generate_document(session, owner_id, document.id)
    return document, True


def _clean(markdown: str) -> str:
    text = markdown.strip()
    fenced = _FENCE.match(text)
    return (fenced.group(1) if fenced else text).strip()


async def write(rt: Runtime, ctx: JobContext) -> None:
    """``document.generate``: write a pending document with the model."""
    document_id = ctx.payload["document_id"]
    async with rt.db.transaction() as session:
        document = await repo.get_any_owner(session, document_id)
        if document is None or document.status != PENDING:
            return  # finished already, or deleted with its application
        application = await applications_repo.get_any_owner(session, document.application_id)
        if application is None:
            return
        owner_id = document.owner_id
        opportunity = await opportunities_repo.get(session, owner_id, application.opportunity_id)
        profile = (
            await profiles_repo.default_for(session, owner_id, opportunity.pack)
            if document.profile_id is None
            else await _profile_or_none(session, owner_id, document.profile_id)
        )
        pack = get_pack(opportunity.pack)
        if profile is None:
            await _fail(session, document, ErrorCode.PROFILE_NOT_FOUND.value)
            return
        person = ProfileInput(
            name=profile.name,
            summary=profile.summary,
            attributes=profile.attributes,
            tone_instructions=profile.tone_instructions,
        )
        letterhead = pack.letterhead(person)
        layout = pack.document_type(document.document_type).layout
        today = datetime.now(UTC).date()
        prompt = pack.document_prompt(
            document.document_type,
            person,
            OpportunityInput(
                title=opportunity.title,
                issuer_name=opportunity.issuer_name,
                attributes=opportunity.attributes,
                source_text=opportunity.source_text,
            ),
            today,
        )

    try:
        reply = await rt.model.chat(prompt.text, purpose=prompt.purpose)
    except LLMError as exc:
        # The person is waiting on this: say what's wrong now (and let them try again), rather than retrying
        # quietly for minutes.
        logger.warning("documents: the model could not write %s: %s", document_id, exc)
        await fail(rt, document_id, exc.code)
        return

    content = _clean(reply.text)
    if not content:
        await fail(rt, document_id, LLMError.EMPTY_REPLY)
        return
    # The header is the profile's, as the template has it, never the model's guess at it.
    content = with_letterhead(content, *letterhead, layout, f"{today:%B} {today.day}, {today.year}")
    async with rt.db.transaction() as session:
        # The application's row lock puts finishing documents for it one after another, so versions never clash.
        await applications_repo.get_any_owner(session, document.application_id, for_update=True)
        document = await repo.get_any_owner(session, document_id, for_update=True)
        if document is None or document.status != PENDING:
            return
        version = await repo.last_version(session, document.application_id, document.document_type) + 1
        await repo.deactivate(session, document.application_id, document.document_type)
        await session.flush()
        document.content_markdown = content
        document.version = version
        document.is_active = True
        document.status = READY
        document.error_code = None
        document.model = reply.model
        document.generation_ms = reply.milliseconds
        document.finished_at = datetime.now(UTC)
        await review.after_written(session, document)


async def _profile_or_none(session: AsyncSession, owner_id: str, profile_id: str):
    try:
        return await profiles_repo.get(session, owner_id, profile_id)
    except NotFound:
        return None


async def _fail(session: AsyncSession, document: ApplicationDocument, code: str) -> None:
    document.status = FAILED
    document.error_code = code
    document.finished_at = datetime.now(UTC)


async def fail(rt: Runtime, document_id: str, code: str) -> None:
    async with rt.db.transaction() as session:
        document = await repo.get_any_owner(session, document_id, for_update=True)
        if document is not None and document.status == PENDING:
            await _fail(session, document, code)


async def give_up(rt: Runtime, ctx: JobContext) -> None:
    """The job failed for good (or its worker died on the last try): the document must not stay pending."""
    await fail(rt, ctx.payload["document_id"], ErrorCode.INTERNAL.value)


async def get(session: AsyncSession, owner_id: str, application_id: str, document_id: str) -> ApplicationDocument:
    return await repo.get(session, owner_id, application_id, document_id)


async def list_(session: AsyncSession, owner_id: str, application_id: str) -> Sequence[ApplicationDocument]:
    await applications_repo.get(session, owner_id, application_id)
    return await repo.of_application(session, owner_id, application_id)
