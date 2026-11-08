"""The packs registry and the pipelines that come with them (rows with no owner)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Pack, Pipeline, Stage


async def lock_sync(session: AsyncSession) -> None:
    """Serialise pack syncs (the API and a worker starting together)."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('apply.packs'))"))


async def upsert_pack(session: AsyncSession, row: dict[str, Any]) -> None:
    stmt = insert(Pack).values(**row, is_active=True)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[Pack.key], set_={k: stmt.excluded[k] for k in (*row.keys(), "is_active") if k != "key"}
        )
    )


async def system_pipeline(session: AsyncSession, pack: str, key: str) -> Pipeline | None:
    return (
        await session.execute(
            select(Pipeline).where(Pipeline.pack == pack, Pipeline.key == key, Pipeline.owner_id.is_(None))
        )
    ).scalar_one_or_none()


async def add(session: AsyncSession, row: Any) -> Any:
    session.add(row)
    await session.flush()
    return row


async def stages_of(session: AsyncSession, pipeline_id: str, *, include_archived: bool = True) -> Sequence[Stage]:
    stmt = select(Stage).where(Stage.pipeline_id == pipeline_id).order_by(Stage.position, Stage.code)
    if not include_archived:
        stmt = stmt.where(Stage.is_archived.is_(False))
    return (await session.execute(stmt)).scalars().all()


async def default_pipeline(session: AsyncSession, pack: str, owner_id: str) -> Pipeline | None:
    """The owner's own default for the pack if they have one, else the pack's."""
    rows = (
        (
            await session.execute(
                select(Pipeline)
                .where(
                    Pipeline.pack == pack,
                    Pipeline.is_default.is_(True),
                    (Pipeline.owner_id == owner_id) | Pipeline.owner_id.is_(None),
                )
                .order_by(Pipeline.owner_id.is_(None))
            )
        )
        .scalars()
        .all()
    )
    return rows[0] if rows else None


async def stage(session: AsyncSession, stage_id: str) -> Stage | None:
    return await session.get(Stage, stage_id)


async def stage_by_code(session: AsyncSession, pipeline_id: str, code: str) -> Stage | None:
    return (
        await session.execute(select(Stage).where(Stage.pipeline_id == pipeline_id, Stage.code == code))
    ).scalar_one_or_none()


async def pipeline_visible(session: AsyncSession, pipeline_id: str, owner_id: str) -> Pipeline | None:
    return (
        await session.execute(
            select(Pipeline).where(
                Pipeline.id == pipeline_id, (Pipeline.owner_id == owner_id) | Pipeline.owner_id.is_(None)
            )
        )
    ).scalar_one_or_none()


async def active_packs(session: AsyncSession) -> Sequence[Pack]:
    return (await session.execute(select(Pack).where(Pack.is_active.is_(True)).order_by(Pack.key))).scalars().all()
