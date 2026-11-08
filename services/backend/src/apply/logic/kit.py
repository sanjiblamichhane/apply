"""
The Application kit: everything needed to apply by hand, in order: the form's address, the documents (the
version in use, its PDF, its warnings), the saved answers, and "I've submitted it".

Submitting records what went out (document versions; answers, sensitive ones only as provided or declined),
stamps the application, and moves a new one to the pack's submitted stage. It can be undone for 10 minutes.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode
from apply.packs import get_pack
from apply.store.sql.models import AutoRun, Submission
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import documents as documents_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import packs as packs_repo
from apply.store.sql.repo import review as repo

from . import answers as answers_logic
from . import applications

UNDO_WINDOW = timedelta(minutes=10)


async def kit(session: AsyncSession, owner_id: str, application_id: str) -> dict[str, Any]:
    application = await applications.get(session, owner_id, application_id)
    opp = await opportunities_repo.get(session, owner_id, application.opportunity_id)
    pack = get_pack(opp.pack)
    docs = [
        d
        for d in await documents_repo.of_application(session, owner_id, application_id)
        if d.is_active and d.status == "ready"
    ]
    if not await repo.answers(session, owner_id, opp.pack):
        await answers_logic.add_defaults(session, owner_id, opp.pack)
    return {
        "application": application,
        "apply_url": opp.apply_url or opp.source_url,
        "documents": [
            {
                "document": d,
                "open_warnings": sum(1 for w in d.claim_warnings if not w.get("resolved")),
                "label": dict(pack.document_type(d.document_type).label),
            }
            for d in docs
        ],
        "answers": await repo.answers(session, owner_id, opp.pack),
        "submissions": await repo.submissions(session, owner_id, application_id),
    }


async def submit(
    session: AsyncSession,
    owner_id: str,
    application_id: str,
    *,
    note: str = "",
    channel: str = "manual",
    details: dict[str, Any] | None = None,
) -> tuple[Submission, bool]:
    """
    Record a submission. Returns it and whether it is new: from the extension or the runner, the same
    application submitted again within the undo window (a reloaded "thank you" page) is the same submission.
    """
    application = await applications_repo.get(session, owner_id, application_id, for_update=True)
    if channel != "manual":
        now = datetime.now(UTC)
        for earlier in await repo.submissions(session, owner_id, application_id):
            if earlier.channel == channel and earlier.undone_at is None and now - earlier.submitted_at <= UNDO_WINDOW:
                return earlier, False
    opp = await opportunities_repo.get(session, owner_id, application.opportunity_id)
    pack = get_pack(opp.pack)
    docs = [
        d
        for d in await documents_repo.of_application(session, owner_id, application_id)
        if d.is_active and d.status == "ready"
    ]
    previous_stage = application.stage_id
    submission = Submission(
        owner_id=owner_id,
        application_id=application_id,
        channel=channel,
        note=note,
        documents=[
            {
                "document_id": d.id,
                "document_type": d.document_type,
                "version": d.version,
                "reviewed": d.reviewed_at is not None,
                "open_warnings": sum(1 for w in d.claim_warnings if not w.get("resolved")),
            }
            for d in docs
        ],
        answers=[answers_logic.recorded(a) for a in await repo.answers(session, owner_id, opp.pack)],
        previous_stage_id=previous_stage,
        details=details or {},
    )
    session.add(submission)
    await session.flush()
    application.submitted_at = datetime.now(UTC)
    # Auto prepared it, and the person sent it.
    await session.execute(
        update(AutoRun)
        .where(
            AutoRun.owner_id == owner_id,
            AutoRun.application_id == application_id,
            AutoRun.status.in_(("starting", "writing", "ready")),
        )
        .values(status="sent", submission_id=submission.id, finished_at=datetime.now(UTC))
    )
    current = await packs_repo.stage(session, application.stage_id)
    if pack.submitted_stage and current is not None and current.position == 0:
        await applications.move(
            session, owner_id, application_id, stage_code=pack.submitted_stage, note="Submitted", outcome="advance"
        )
    await session.flush()
    return submission, True


async def undo(session: AsyncSession, owner_id: str, submission_id: str) -> Submission:
    submission = await repo.submission(session, owner_id, submission_id, for_update=True)
    if submission.undone_at is not None:
        return submission
    if datetime.now(UTC) - submission.submitted_at > UNDO_WINDOW:
        raise Conflict(ErrorCode.UNDO_TOO_LATE, "A submission can be undone for 10 minutes")
    submission.undone_at = datetime.now(UTC)
    # Not sent after all: an Auto run it finished is Ready for you again.
    await session.execute(
        update(AutoRun)
        .where(AutoRun.owner_id == owner_id, AutoRun.submission_id == submission.id, AutoRun.status == "sent")
        .values(status="ready", submission_id=None, finished_at=None)
    )
    application = await applications_repo.get(session, owner_id, submission.application_id, for_update=True)
    others = [
        s
        for s in await repo.submissions(session, owner_id, application.id)
        if s.id != submission.id and s.undone_at is None
    ]
    application.submitted_at = others[0].submitted_at if others else None
    if submission.previous_stage_id and application.stage_id != submission.previous_stage_id:
        stage = await packs_repo.stage(session, submission.previous_stage_id)
        if stage is not None:
            await applications.move(
                session, owner_id, application.id, stage_code=stage.code, note="Submission undone", outcome="back"
            )
    await session.flush()
    return submission
