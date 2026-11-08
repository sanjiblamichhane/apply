"""
Each person's templates for their documents: one for resumes, one for letters (libs/render/template.py). The
defaults until they upload their own; an upload is kept only if it passes every check (libs/render/checks.py),
and their documents' files are made again in it the next time they're asked for.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, InvalidArgument
from apply.libs.render import Kind, Problem, check_template, default_template, parts, sample

__all__ = ["check", "default_template", "mine", "preview", "reset", "save", "template"]
from apply.libs.render.template import fill
from apply.store.sql.models import DocumentTemplate

SAMPLE_TITLE = {"sections": "Lorem Ipsum - Resume", "letter": "Lorem Ipsum - Cover Letter"}


async def mine(session: AsyncSession, owner_id: str, kind: Kind) -> DocumentTemplate | None:
    return await session.scalar(
        select(DocumentTemplate).where(DocumentTemplate.owner_id == owner_id, DocumentTemplate.kind == kind)
    )


async def template(session: AsyncSession, owner_id: str, kind: Kind) -> str:
    """The template a document of this kind is made in: theirs, or the default."""
    found = await mine(session, owner_id, kind)
    return found.html if found else default_template(kind)


def preview(html: str, kind: Kind) -> str:
    """The template filled with the sample: what a document in it looks like."""
    return fill(html, parts(sample(kind), kind), title=SAMPLE_TITLE[kind], description="A sample, to see the template.")


def check(html: str, kind: Kind) -> list[Problem]:
    return check_template(html, kind)


async def save(session: AsyncSession, owner_id: str, kind: Kind, html: str, filename: str) -> DocumentTemplate:
    problems = check(html, kind)
    if problems:
        raise InvalidArgument(
            ErrorCode.TEMPLATE_PROBLEMS,
            f"The template has {len(problems)} problem(s) to fix first",
            extra={"problems": [{"code": p.code, "message": p.message, "wcag": p.wcag} for p in problems]},
        )
    found = await mine(session, owner_id, kind)
    if found is None:
        found = DocumentTemplate(owner_id=owner_id, kind=kind, html=html, filename=filename)
        session.add(found)
    else:
        found.html, found.filename = html, filename
    await session.flush()
    return found


async def reset(session: AsyncSession, owner_id: str, kind: Kind) -> None:
    found = await mine(session, owner_id, kind)
    if found is not None:
        await session.delete(found)
        await session.flush()
