"""
The kinds of background job apply runs, their queues and priorities.

Model work goes to the ``llm`` queue, run one at a time (a local model server answers one request at a time; two at once
only time each other out). A click someone is waiting on outranks background work.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from apply.libs.jobs import enqueue
from apply.store.sql.models import jobs

LLM, DEFAULT = "llm", "default"
QUEUES = (LLM, DEFAULT)
INTERACTIVE, BACKGROUND = 100, 0

EXTRACT_OPPORTUNITY = "opportunity.extract"
GENERATE_DOCUMENT = "document.generate"
FETCH_SOURCE = "source.fetch"
RUN_SEARCH = "search.run"
SCORE_MATCH = "match.score"
BUILD_BRIEFING = "briefing.build"
CHECK_DOCUMENT = "document.check"
RENDER_DOCUMENT = "document.render"
READ_PROFILE = "profile.read"


async def extract_opportunity(session: AsyncSession, owner_id: str, opportunity_id: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=EXTRACT_OPPORTUNITY,
        queue=LLM,
        priority=INTERACTIVE,
        max_attempts=3,
        key=opportunity_id,
        owner_id=owner_id,
        payload={"opportunity_id": opportunity_id},
    )


async def read_profile(session: AsyncSession, owner_id: str, profile_id: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=READ_PROFILE,
        queue=LLM,
        priority=INTERACTIVE,
        max_attempts=2,
        key=f"read:{profile_id}",
        owner_id=owner_id,
        payload={"profile_id": profile_id},
    )


async def generate_document(session: AsyncSession, owner_id: str, document_id: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=GENERATE_DOCUMENT,
        queue=LLM,
        priority=INTERACTIVE,
        max_attempts=3,
        key=document_id,
        owner_id=owner_id,
        payload={"document_id": document_id},
    )


async def fetch_source(
    session: AsyncSession, owner_id: str, source_id: str, *, interactive: bool = False
) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=FETCH_SOURCE,
        queue=DEFAULT,
        priority=INTERACTIVE if interactive else 0,
        max_attempts=2,
        key=f"source:{source_id}",
        owner_id=owner_id,
        payload={"source_id": source_id},
    )


async def run_search(session: AsyncSession, owner_id: str, search_id: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=RUN_SEARCH,
        queue=DEFAULT,
        priority=INTERACTIVE,
        max_attempts=2,
        key=f"search:{search_id}",
        owner_id=owner_id,
        payload={"search_id": search_id},
    )


async def score_match(
    session: AsyncSession, owner_id: str, match_id: str, *, run_after=None, key_suffix: str = ""
) -> str | None:
    """Scoring is background work: an interactive click (writing a document) goes first."""
    return await enqueue(
        session,
        jobs,
        kind=SCORE_MATCH,
        queue=LLM,
        priority=BACKGROUND,
        max_attempts=2,
        key=f"match:{match_id}{key_suffix}",
        owner_id=owner_id,
        run_after=run_after,
        payload={"match_id": match_id},
    )


async def build_briefing(session: AsyncSession, owner_id: str, date: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=BUILD_BRIEFING,
        queue=DEFAULT,
        priority=BACKGROUND,
        max_attempts=3,
        key=f"briefing:{owner_id}:{date}",
        owner_id=owner_id,
        payload={"owner_id": owner_id, "date": date},
    )


async def check_document(session: AsyncSession, owner_id: str, document_id: str) -> str | None:
    """The claim check: the person is about to read the document, so it goes ahead of background scoring."""
    return await enqueue(
        session,
        jobs,
        kind=CHECK_DOCUMENT,
        queue=LLM,
        priority=INTERACTIVE,
        max_attempts=2,
        key=f"check:{document_id}",
        owner_id=owner_id,
        payload={"document_id": document_id},
    )


async def render_document(session: AsyncSession, owner_id: str, document_id: str) -> str | None:
    return await enqueue(
        session,
        jobs,
        kind=RENDER_DOCUMENT,
        queue=DEFAULT,
        priority=INTERACTIVE,
        max_attempts=3,
        key=f"render:{document_id}",
        owner_id=owner_id,
        payload={"document_id": document_id},
    )
