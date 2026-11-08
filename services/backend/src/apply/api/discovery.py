"""The discovery API: sources, searches, the matches inbox and today's briefing (routes under /api/v1)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from apply.logic import briefings, matches, searches, sources
from apply.packs import DEFAULT_PACK, get_pack
from apply.store.sql.models import User

from . import schemas as s
from .deps import Rt, current_user

Owner = Annotated[User, Depends(current_user)]
discovery = APIRouter()


# ── sources ──────────────────────────────────────────────────────────────────


@discovery.get("/source-kinds", tags=["discovery"])
async def list_source_kinds(_user: Owner, pack: str = DEFAULT_PACK) -> s.SourceKinds:
    """Where postings can come from, what each needs, and what its terms ask of us."""
    return s.SourceKinds(items=[s.SourceKind(**adapter.describe()) for adapter in get_pack(pack).sources])


@discovery.get("/sources", tags=["discovery"])
async def list_sources(rt: Rt, user: Owner, pack: str | None = None) -> s.Sources:
    async with rt.db.transaction() as session:
        return s.Sources(items=[s.SourceOut.model_validate(x) for x in await sources.list_(session, user.id, pack)])


@discovery.post("/sources", tags=["discovery"], status_code=status.HTTP_201_CREATED)
async def create_source(body: s.NewSource, rt: Rt, user: Owner) -> s.SourceOut:
    """Add a source; it's fetched straight away, then on its schedule."""
    async with rt.db.transaction() as session:
        return s.SourceOut.model_validate(await sources.create(session, user.id, **body.model_dump()))


@discovery.post("/sources/recognise", tags=["discovery"])
async def recognise_source(body: s.SourceAddress, _user: Owner) -> s.RecognisedSource:
    """Which kind of source a pasted address is (a company's job board page), and the config it stands for."""
    kind, config = sources.recognise(body.pack, body.url)
    return s.RecognisedSource(kind=kind, config=config)


@discovery.get("/sources/{source_id}", tags=["discovery"])
async def get_source(source_id: str, rt: Rt, user: Owner) -> s.SourceOut:
    async with rt.db.transaction() as session:
        return s.SourceOut.model_validate(await sources.get(session, user.id, source_id))


@discovery.patch("/sources/{source_id}", tags=["discovery"])
async def update_source(source_id: str, body: s.SourceChanges, rt: Rt, user: Owner) -> s.SourceOut:
    async with rt.db.transaction() as session:
        changes = body.model_dump(exclude_unset=True)
        return s.SourceOut.model_validate(await sources.update(session, user.id, source_id, changes))


@discovery.delete("/sources/{source_id}", tags=["discovery"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, rt: Rt, user: Owner) -> None:
    async with rt.db.transaction() as session:
        await sources.delete(session, user.id, source_id)


@discovery.post("/sources/{source_id}/fetch", tags=["discovery"], status_code=status.HTTP_202_ACCEPTED)
async def fetch_source(source_id: str, rt: Rt, user: Owner) -> s.SourceOut:
    """Fetch now (409 SOURCE_TOO_SOON within the interval the source's terms ask for)."""
    async with rt.db.transaction() as session:
        return s.SourceOut.model_validate(await sources.fetch_now(session, user.id, source_id))


# ── searches ─────────────────────────────────────────────────────────────────


@discovery.get("/searches", tags=["discovery"])
async def list_searches(rt: Rt, user: Owner, pack: str | None = None) -> s.Searches:
    async with rt.db.transaction() as session:
        return s.Searches(items=[s.SearchOut.model_validate(x) for x in await searches.list_(session, user.id, pack)])


@discovery.post("/searches", tags=["discovery"], status_code=status.HTTP_201_CREATED)
async def create_search(body: s.NewSearch, rt: Rt, user: Owner) -> s.SearchOut:
    """Save a search; it runs over what's already here straight away, then on every fetch."""
    async with rt.db.transaction() as session:
        values = body.model_dump()
        return s.SearchOut.model_validate(await searches.create(session, user.id, **values))


@discovery.get("/searches/{search_id}", tags=["discovery"])
async def get_search(search_id: str, rt: Rt, user: Owner) -> s.SearchOut:
    async with rt.db.transaction() as session:
        return s.SearchOut.model_validate(await searches.get(session, user.id, search_id))


@discovery.patch("/searches/{search_id}", tags=["discovery"])
async def update_search(search_id: str, body: s.SearchChanges, rt: Rt, user: Owner) -> s.SearchOut:
    async with rt.db.transaction() as session:
        changes = body.model_dump(exclude_unset=True)
        return s.SearchOut.model_validate(await searches.update(session, user.id, search_id, changes))


@discovery.delete("/searches/{search_id}", tags=["discovery"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(search_id: str, rt: Rt, user: Owner) -> None:
    async with rt.db.transaction() as session:
        await searches.delete(session, user.id, search_id)


# ── matches ──────────────────────────────────────────────────────────────────


@discovery.get("/matches", tags=["discovery"])
async def list_matches(
    rt: Rt,
    user: Owner,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    search_id: str | None = None,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    after: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    pack: str | None = None,
) -> s.Matches:
    """The inbox: best fit first (unscored last), then newest. Default: new and saved."""
    async with rt.db.transaction() as session:
        rows, cursor = await matches.inbox(
            session,
            user.id,
            statuses=status_ or ["new", "saved"],
            search_id=search_id,
            min_score=min_score,
            after=after,
            limit=limit,
            pack=pack,
        )
        counts = await matches.counts(session, user.id, pack)
        return s.Matches(
            items=[s.MatchOut.model_validate(m) for m in rows], next_cursor=cursor, counts=s.MatchCounts(**counts)
        )


@discovery.patch("/matches/{match_id}", tags=["discovery"])
async def update_match(match_id: str, body: s.MatchChanges, rt: Rt, user: Owner) -> s.MatchOut:
    """Save, dismiss, or put back (undo)."""
    async with rt.db.transaction() as session:
        return s.MatchOut.model_validate(await matches.set_status(session, user.id, match_id, body.status))


@discovery.post("/matches/{match_id}/track", tags=["discovery"])
async def track_match(match_id: str, rt: Rt, user: Owner) -> s.Tracked:
    """Make it an application (or point it at the one already tracking this job)."""
    async with rt.db.transaction() as session:
        match, application_id = await matches.track(session, user.id, match_id)
        return s.Tracked(match=s.MatchOut.model_validate(match), application_id=application_id)


# ── briefing ─────────────────────────────────────────────────────────────────


@discovery.get("/briefings/today", tags=["discovery"], responses={204: {"description": "Not built yet today"}})
async def todays_briefing(rt: Rt, user: Owner) -> s.BriefingOut | None:
    """Today's briefing, in the owner's time zone; built at their briefing hour (or POST to build it now)."""
    async with rt.db.transaction() as session:
        found = await briefings.today(session, user.id, user)
        return s.BriefingOut.model_validate(found) if found else None


@discovery.post("/briefings/today", tags=["discovery"])
async def build_todays_briefing(rt: Rt, user: Owner) -> s.BriefingOut:
    async with rt.db.transaction() as session:
        date = briefings.local_date(user, datetime.now(UTC))
        return s.BriefingOut.model_validate(await briefings.build(session, user.id, date))
