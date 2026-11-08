"""
Applications: one owner applying to one opportunity, with a profile, moving through the pack's pipeline.

Every stage change closes the open history entry and opens a new one, so time in each stage can be measured.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy import update as update_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument, NotFound
from apply.store.sql.models import Application, AutoRun, Match, Stage, StageHistory
from apply.store.sql.repo import applications as repo
from apply.store.sql.repo import auto as auto_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import packs as packs_repo
from apply.store.sql.repo import profiles as profiles_repo


async def create(
    session: AsyncSession, owner_id: str, *, opportunity_id: str, profile_id: str | None, notes: str = ""
) -> Application:
    opportunity = await opportunities_repo.get(session, owner_id, opportunity_id)
    existing = await repo.by_opportunity(session, owner_id, opportunity_id)
    if existing is not None:
        raise Conflict(
            ErrorCode.APPLICATION_EXISTS,
            "There is already an application for this opportunity",
            extra={"application_id": existing.id},
        )
    profile = await _profile_for(session, owner_id, opportunity.pack, profile_id)
    pipeline = await packs_repo.default_pipeline(session, opportunity.pack, owner_id)
    if pipeline is None:
        raise NotFound(ErrorCode.PACK_NOT_FOUND, f"The {opportunity.pack} pack has no pipeline")
    stages = await packs_repo.stages_of(session, pipeline.id, include_archived=False)
    if not stages:
        raise NotFound(ErrorCode.STAGE_NOT_FOUND, f"The {pipeline.key} pipeline has no stages")
    first = stages[0]
    try:
        async with session.begin_nested():
            application = await repo.add(
                session,
                owner_id=owner_id,
                opportunity_id=opportunity.id,
                profile_id=profile.id if profile else None,
                pipeline_id=pipeline.id,
                stage_id=first.id,
                notes=notes,
            )
    except IntegrityError:
        found = await repo.by_opportunity(session, owner_id, opportunity_id)
        raise Conflict(
            ErrorCode.APPLICATION_EXISTS,
            "There is already an application for this opportunity",
            extra={"application_id": found.id if found else None},
        ) from None
    await repo.add_history(session, owner_id=owner_id, application_id=application.id, stage_id=first.id, note="")
    return await repo.loaded(session, application)


async def _profile_for(session: AsyncSession, owner_id: str, pack: str, profile_id: str | None):
    if profile_id is None:
        return await profiles_repo.default_for(session, owner_id, pack)
    profile = await profiles_repo.get(session, owner_id, profile_id)
    if profile.pack != pack:
        raise InvalidArgument(
            ErrorCode.PROFILE_PACK_MISMATCH, f"That profile is for the {profile.pack} pack, not {pack}"
        )
    return profile


async def update(session: AsyncSession, owner_id: str, application_id: str, changes: dict[str, Any]) -> Application:
    application = await repo.get(session, owner_id, application_id, for_update=True)
    if "profile_id" in changes:
        opportunity = await opportunities_repo.get(session, owner_id, application.opportunity_id)
        profile = (
            await _profile_for(session, owner_id, opportunity.pack, changes["profile_id"])
            if changes["profile_id"]
            else None
        )
        application.profile_id = profile.id if profile else None
    if "notes" in changes and changes["notes"] is not None:
        application.notes = changes["notes"]
    return await repo.loaded(session, application)


async def delete(session: AsyncSession, owner_id: str, application_id: str) -> None:
    """
    The application gone, with its documents (their files leave the bucket on the next sweep), history and
    submissions. Its posting stays. An Auto run preparing it stops, and a match that tracked it goes back to saved.
    """
    application = await repo.get(session, owner_id, application_id, for_update=True)
    runs = (
        (await session.execute(select(AutoRun).where(AutoRun.application_id == application.id).with_for_update()))
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    for run in runs:
        if run.status in (*auto_repo.ACTIVE, "ready"):
            run.status, run.finished_at = "stopped", now
    await session.execute(
        update_(Match)
        .where(Match.application_id == application.id, Match.status == "tracked")
        .values(status="saved", status_changed_at=now)
    )
    await session.delete(application)
    await session.flush()


async def move(
    session: AsyncSession, owner_id: str, application_id: str, *, stage_code: str, note: str = "", outcome: str = ""
) -> Application:
    application = await repo.get(session, owner_id, application_id, for_update=True)
    stage = await packs_repo.stage_by_code(session, application.pipeline_id, stage_code)
    if stage is None or stage.is_archived:
        raise InvalidArgument(ErrorCode.STAGE_NOT_FOUND, f"The pipeline has no stage {stage_code!r}")
    if stage.id == application.stage_id:
        return await repo.loaded(session, application)
    current = await packs_repo.stage(session, application.stage_id)
    if not outcome and current is not None:
        outcome = _outcome(current, stage)
    await repo.close_history(session, application.id, outcome)
    await repo.add_history(session, owner_id=owner_id, application_id=application.id, stage_id=stage.id, note=note)
    application.stage_id = stage.id
    application.updated_at = datetime.now(UTC)
    return await repo.loaded(session, application)


def _outcome(left: Stage, entered: Stage) -> str:
    if entered.category == "failure":
        return "reject"
    if entered.category == "paused":
        return "hold"
    return "advance" if entered.position > left.position else "back"


async def get(session: AsyncSession, owner_id: str, application_id: str) -> Application:
    return await repo.loaded(session, await repo.get(session, owner_id, application_id))


async def list_(
    session: AsyncSession, owner_id: str, *, pack: str | None, stage_code: str | None, after: str | None, limit: int
) -> tuple[Sequence[Application], str | None]:
    stage_id = None
    if stage_code:
        if not pack:
            raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "Filtering by stage needs the pack too")
        pipeline = await packs_repo.default_pipeline(session, pack, owner_id)
        stage = await packs_repo.stage_by_code(session, pipeline.id, stage_code) if pipeline else None
        if stage is None:
            raise InvalidArgument(ErrorCode.STAGE_NOT_FOUND, f"No stage {stage_code!r}")
        stage_id = stage.id
    return await repo.list_(session, owner_id, pack=pack, stage_id=stage_id, after=after, limit=limit)


async def history(session: AsyncSession, owner_id: str, application_id: str) -> Sequence[StageHistory]:
    await repo.get(session, owner_id, application_id)
    return await repo.history(session, owner_id, application_id)
