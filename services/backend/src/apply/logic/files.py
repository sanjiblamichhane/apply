"""
The files apply keeps in the bucket (libs/storage): a PDF of a document version, Auto's screenshots, and the
document a profile was read from. A row holds the key; the bucket holds the bytes.

A file is put in the bucket before its row is saved, so a row never points at nothing; a file whose row didn't
save, or whose row is gone (deleted with its application, run or profile), is removed by ``sweep`` once it's an
hour old. Bytes kept in the database before migration 0009 are moved to the bucket by ``move_from_database``.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, Unavailable
from apply.libs.storage import StorageError, document_pdf, screenshot
from apply.runtime import Runtime
from apply.store.sql.models import AutoScreenshot, Profile, RenderedFile

logger = logging.getLogger("apply.files")

PDF = "application/pdf"
HTML = "text/html; charset=utf-8"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PNG = "image/png"
SWEEP_AFTER = timedelta(hours=1)  # younger than this, a file without a row may be one whose row is being saved
MOVE_BATCH = 50

Kept = RenderedFile | AutoScreenshot


async def put(rt: Runtime, key: str, data: bytes, content_type: str) -> None:
    try:
        await rt.files.put(key, data, content_type)
    except StorageError as exc:
        logger.error("files: couldn't keep %s: %s", key, exc)
        raise Unavailable(ErrorCode.STORAGE_UNAVAILABLE, "The file bucket can't be reached") from exc


async def get(rt: Runtime, session: AsyncSession, row: Kept) -> bytes:
    """A kept file's bytes: from the bucket, or (not yet moved) the database."""
    if row.object_key is None:
        data = (await session.execute(select(type(row).data).where(type(row).id == row.id))).scalar_one()
        return data or b""
    try:
        data = await rt.files.get(row.object_key)
    except StorageError as exc:
        logger.error("files: couldn't read %s: %s", row.object_key, exc)
        raise Unavailable(ErrorCode.STORAGE_UNAVAILABLE, "The file bucket can't be reached") from exc
    if data is None:
        logger.error("files: %s is missing from the bucket", row.object_key)
        raise Unavailable(ErrorCode.STORAGE_UNAVAILABLE, "The file is missing from the bucket")
    return data


async def get_key(rt: Runtime, key: str) -> bytes | None:
    try:
        return await rt.files.get(key)
    except StorageError as exc:
        raise Unavailable(ErrorCode.STORAGE_UNAVAILABLE, "The file bucket can't be reached") from exc


async def delete(rt: Runtime, *keys: str) -> None:
    """Best effort: what can't be removed now, ``sweep`` removes later."""
    try:
        await rt.files.delete(*keys)
    except StorageError as exc:
        logger.warning("files: couldn't remove %s yet: %s", keys, exc)


# ── on start: bytes from before migration 0009 ───────────────────────────────


async def move_from_database(rt: Runtime) -> int:
    """Each PDF and screenshot still kept in the database, put in the bucket and its bytes dropped here."""
    moved = 0
    for model, key_of, content_type in (
        (RenderedFile, lambda r: document_pdf(r.owner_id, r.document_id, r.sha256), PDF),
        (AutoScreenshot, lambda r: screenshot(r.owner_id, r.run_id, r.id), PNG),
    ):
        while True:
            async with rt.db.transaction() as session:
                rows = (
                    await session.execute(
                        select(model, model.data)
                        .where(model.data.is_not(None))
                        .limit(MOVE_BATCH)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
                if not rows:
                    break
                for row, data in rows:
                    key = key_of(row)
                    await rt.files.put(key, data, content_type)
                    await session.execute(update(model).where(model.id == row.id).values(object_key=key, data=None))
                    moved += 1
    if moved:
        logger.info("files: moved %d from the database to the bucket", moved)
    return moved


# ── now and then: files nothing points at ────────────────────────────────────


async def sweep(rt: Runtime, *, now: datetime | None = None) -> int:
    """Remove the bucket's files that no row points at (and that are older than an hour)."""
    cutoff = (now or datetime.now(UTC)) - SWEEP_AFTER
    found = [f for f in await rt.files.files("owners/") if f.updated is None or f.updated < cutoff]
    if not found:
        return 0
    keys = sorted({f.key for f in found})
    kept: set[str] = set()
    source_key = Profile.source["key"].astext
    async with rt.db.transaction() as session:
        for start in range(0, len(keys), 500):
            chunk = keys[start : start + 500]
            for column in (RenderedFile.object_key, AutoScreenshot.object_key, source_key):
                kept |= set((await session.execute(select(column).where(column.in_(chunk)))).scalars())
    orphans = [k for k in keys if k not in kept]
    await rt.files.delete(*orphans)
    if orphans:
        logger.info("files: removed %d that nothing pointed at", len(orphans))
    return len(orphans)
