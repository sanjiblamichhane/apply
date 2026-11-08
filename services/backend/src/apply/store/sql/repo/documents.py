"""Documents written or uploaded for an application."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, NotFound

from ..models import ApplicationDocument
from . import get_owned


async def get(session: AsyncSession, owner_id: str, application_id: str, document_id: str) -> ApplicationDocument:
    doc = await get_owned(session, ApplicationDocument, owner_id, document_id, ErrorCode.DOCUMENT_NOT_FOUND)
    if doc.application_id != application_id:
        raise NotFound(ErrorCode.DOCUMENT_NOT_FOUND, "That document belongs to another application")
    return doc


async def get_any_owner(
    session: AsyncSession, document_id: str, *, for_update: bool = False
) -> ApplicationDocument | None:
    stmt = select(ApplicationDocument).where(ApplicationDocument.id == document_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def pending(session: AsyncSession, application_id: str, document_type: str) -> ApplicationDocument | None:
    return (
        await session.execute(
            select(ApplicationDocument).where(
                ApplicationDocument.application_id == application_id,
                ApplicationDocument.document_type == document_type,
                ApplicationDocument.status == "pending",
            )
        )
    ).scalar_one_or_none()


async def add(session: AsyncSession, **values: Any) -> ApplicationDocument:
    row = ApplicationDocument(**values)
    session.add(row)
    await session.flush()
    return row


async def last_version(session: AsyncSession, application_id: str, document_type: str) -> int:
    return (
        await session.execute(
            select(func.coalesce(func.max(ApplicationDocument.version), 0)).where(
                ApplicationDocument.application_id == application_id, ApplicationDocument.document_type == document_type
            )
        )
    ).scalar_one()


async def deactivate(session: AsyncSession, application_id: str, document_type: str) -> None:
    await session.execute(
        update(ApplicationDocument)
        .where(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type == document_type,
            ApplicationDocument.is_active.is_(True),
        )
        .values(is_active=False)
    )


async def of_application(session: AsyncSession, owner_id: str, application_id: str) -> Sequence[ApplicationDocument]:
    return (
        (
            await session.execute(
                select(ApplicationDocument)
                .where(ApplicationDocument.owner_id == owner_id, ApplicationDocument.application_id == application_id)
                .order_by(ApplicationDocument.document_type, ApplicationDocument.id.desc())
            )
        )
        .scalars()
        .all()
    )
