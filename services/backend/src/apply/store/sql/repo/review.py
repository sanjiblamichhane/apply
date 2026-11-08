"""Rendered files, saved answers and submissions."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode

from ..models import Answer, RenderedFile, Submission
from . import get_owned


async def rendered(session: AsyncSession, document_id: str, kind: str, sha256: str) -> RenderedFile | None:
    return (
        await session.execute(
            select(RenderedFile).where(
                RenderedFile.document_id == document_id, RenderedFile.kind == kind, RenderedFile.sha256 == sha256
            )
        )
    ).scalar_one_or_none()


async def answers(session: AsyncSession, owner_id: str, pack: str) -> Sequence[Answer]:
    return (
        (
            await session.execute(
                select(Answer)
                .where(Answer.owner_id == owner_id, Answer.pack == pack)
                .order_by(Answer.position, Answer.id)
            )
        )
        .scalars()
        .all()
    )


async def answer(session: AsyncSession, owner_id: str, answer_id: str, *, for_update: bool = False) -> Answer:
    return await get_owned(session, Answer, owner_id, answer_id, ErrorCode.ANSWER_NOT_FOUND, for_update=for_update)


async def submissions(session: AsyncSession, owner_id: str, application_id: str) -> Sequence[Submission]:
    return (
        (
            await session.execute(
                select(Submission)
                .where(Submission.owner_id == owner_id, Submission.application_id == application_id)
                .order_by(Submission.id.desc())
            )
        )
        .scalars()
        .all()
    )


async def submission(
    session: AsyncSession, owner_id: str, submission_id: str, *, for_update: bool = False
) -> Submission:
    return await get_owned(
        session, Submission, owner_id, submission_id, ErrorCode.SUBMISSION_NOT_FOUND, for_update=for_update
    )
