"""Auto: its settings, the runs (being prepared, Ready for you, Needs you) and the person's actions on them.
Nothing here sends an application: the person does. Routes under /api/v1."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from apply.errors import ErrorCode, NotFound
from apply.logic import auto, files
from apply.store.sql.models import AutoRun, User
from apply.store.sql.repo import auto as repo

from . import schemas as s
from .deps import Rt, current_user

Owner = Annotated[User, Depends(current_user)]
automatic = APIRouter()
GROUPS = {
    "waiting": list(repo.ACTIVE),
    "ready": ["ready"],
    "needs_you": ["needs_you"],
    "done": ["sent", "stopped", "dismissed"],
}


async def _out(session, run: AutoRun) -> s.AutoRunOut:
    shots = await repo.screenshots(session, run.owner_id, run.id)  # from runs a runner sent, before
    return s.AutoRunOut(
        id=run.id,
        status=run.status,  # type: ignore[arg-type]
        reason=run.reason,  # type: ignore[arg-type]
        reason_detail=run.reason_detail or {},
        match_id=run.match_id,
        application_id=run.application_id,
        search_id=run.search_id,
        opportunity=s.OpportunitySummary.model_validate(run.match.opportunity),
        score=run.match.score,
        ready_at=run.ready_at,
        drafts=run.drafts or [],
        screenshots=[s.AutoScreenshotRef(id=i, step=st, size=n) for i, st, n in shots],
        submission_id=run.submission_id,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finished_at=run.finished_at,
    )


@automatic.get("/auto/settings", tags=["auto"])
async def auto_settings(user: Owner) -> s.AutoSettings:
    return s.AutoSettings.model_validate(user)


@automatic.patch("/auto/settings", tags=["auto"])
async def update_auto_settings(body: s.AutoSettingsChanges, rt: Rt, user: Owner) -> s.AutoSettings:
    """Pause Auto (no new runs, and none prepared further), and its limits."""
    async with rt.db.transaction() as session:
        changed = await auto.update_settings(session, user.id, body.model_dump(exclude_unset=True))
        return s.AutoSettings.model_validate(changed)


@automatic.get("/auto/counts", tags=["auto"])
async def auto_counts(rt: Rt, user: Owner) -> s.AutoCounts:
    async with rt.db.transaction() as session:
        counts = await repo.counts(session, user.id)
    return s.AutoCounts(
        waiting=sum(counts.get(k, 0) for k in repo.ACTIVE),
        ready=counts.get("ready", 0),
        needs_you=counts.get("needs_you", 0),
        sent=counts.get("sent", 0),
    )


@automatic.get("/auto/runs", tags=["auto"])
async def list_runs(
    rt: Rt, user: Owner, group: Annotated[str, Query(pattern="^(waiting|ready|needs_you|done)$")] = "waiting"
) -> s.AutoRuns:
    async with rt.db.transaction() as session:
        runs = await repo.runs(session, user.id, GROUPS[group])
        return s.AutoRuns(items=[await _out(session, r) for r in runs])


@automatic.get("/auto/runs/{run_id}", tags=["auto"])
async def get_run(run_id: str, rt: Rt, user: Owner) -> s.AutoRunOut:
    async with rt.db.transaction() as session:
        return await _out(session, await repo.loaded(session, user.id, run_id))


async def _act(rt, user: User, run_id: str, action) -> s.AutoRunOut:
    async with rt.db.transaction() as session:
        await action(session, user.id, run_id)
        await session.flush()
        return await _out(session, await repo.loaded(session, user.id, run_id))


@automatic.post("/auto/runs/{run_id}/stop", tags=["auto"])
async def stop_run(run_id: str, rt: Rt, user: Owner) -> s.AutoRunOut:
    """Stop preparing it, or take it off Ready for you. Its application and documents stay."""
    return await _act(rt, user, run_id, auto.stop)


@automatic.post("/auto/runs/{run_id}/retry", tags=["auto"])
async def retry_run(run_id: str, rt: Rt, user: Owner) -> s.AutoRunOut:
    """Start again from the gate, once what it needed is fixed. Not after a send (from before) that may have gone."""
    return await _act(rt, user, run_id, lambda session, owner, rid: auto.retry(session, rt.settings, owner, rid))


@automatic.post("/auto/runs/{run_id}/dismiss", tags=["auto"])
async def dismiss_run(run_id: str, rt: Rt, user: Owner) -> s.AutoRunOut:
    return await _act(rt, user, run_id, auto.dismiss)


# What a runner's browser showed, on runs from before apply stopped sending: kept as their history.
@automatic.get(
    "/auto/runs/{run_id}/screenshots/{screenshot_id}",
    tags=["auto"],
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "The screenshot"}},
)
async def run_screenshot(run_id: str, screenshot_id: str, rt: Rt, user: Owner) -> Response:
    async with rt.db.transaction() as session:
        shot = await repo.screenshot(session, user.id, run_id, screenshot_id)
        if shot is None:
            raise NotFound(ErrorCode.NOT_FOUND, "No such screenshot")
        data = await files.get(rt, session, shot)
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
