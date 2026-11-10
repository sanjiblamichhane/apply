"""
Files live in the bucket, never the database or the disk: a document's PDF and Auto's screenshots; bytes kept in
the database before migration 0009 move there on start; files nothing points at are swept; and a bucket that
can't be reached is a clear 503, not a crash.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from apply.libs.storage import Storage, StorageConfig
from apply.logic import files
from apply.store.sql.models import RenderedFile

from .test_review_and_kit import model, poll_pdf, written


async def a_pdf(client, model_server, worker) -> tuple[str, bytes]:
    model(model_server)
    app_id, doc = await written(client, worker)
    path = f"/api/v1/applications/{app_id}/documents/{doc['id']}/pdf"
    return path, (await poll_pdf(client, path)).content


async def test_a_pdf_is_kept_in_the_bucket_with_only_its_key_in_the_database(client, owner, model_server, worker, rt):
    _, pdf = await a_pdf(client, model_server, worker)
    async with rt.db.transaction() as session:
        row = (await session.execute(select(RenderedFile).where(RenderedFile.kind == "pdf"))).scalar_one()
        in_database = (await session.execute(select(RenderedFile.data).where(RenderedFile.kind == "pdf"))).scalar_one()
    assert in_database is None
    assert row.object_key == f"owners/{row.owner_id}/documents/{row.document_id}/{row.sha256}.pdf"
    assert await rt.files.get(row.object_key) == pdf


async def test_bytes_from_before_the_bucket_move_there_on_start(client, owner, model_server, worker, rt):
    path, pdf = await a_pdf(client, model_server, worker)
    async with rt.db.transaction() as session:  # as a PDF made before 0009 was kept
        row = (await session.execute(select(RenderedFile).where(RenderedFile.kind == "pdf"))).scalar_one()
        await session.execute(
            text("UPDATE rendered_files SET data = :d, object_key = NULL WHERE id = :id"), {"d": pdf, "id": row.id}
        )
    await rt.files.delete_prefix("owners/")
    assert (await client.get(path)).content == pdf  # still served, from the database, until moved

    assert await files.move_from_database(rt) == 1
    assert await files.move_from_database(rt) == 0  # once only
    async with rt.db.transaction() as session:
        key, data = (
            await session.execute(select(RenderedFile.object_key, RenderedFile.data).where(RenderedFile.kind == "pdf"))
        ).one()
    assert data is None and await rt.files.get(key) == pdf
    assert (await client.get(path)).content == pdf


async def test_files_nothing_points_at_are_swept_once_an_hour_old(client, owner, model_server, worker, rt):
    _, _pdf = await a_pdf(client, model_server, worker)
    async with rt.db.transaction() as session:
        kept = (await session.execute(select(RenderedFile.object_key).where(RenderedFile.kind == "pdf"))).scalar_one()
    orphan = kept.rsplit("/", 1)[0] + "/0000.pdf"
    await rt.files.put(orphan, b"%PDF-1.7 left behind", "application/pdf")

    assert await files.sweep(rt) == 0  # too new: its row may still be on its way
    assert await files.sweep(rt, now=datetime.now(UTC) + timedelta(hours=2)) == 1
    assert sorted(f.key for f in await rt.files.files("owners/")) == sorted(
        kept.removesuffix(".pdf") + f".{k}" for k in ("docx", "html", "pdf")
    )


async def test_a_bucket_that_cant_be_reached_is_a_503_and_health_says_so(client, owner, model_server, worker, rt):
    path, _ = await a_pdf(client, model_server, worker)
    reachable = rt.files
    rt.files = Storage(StorageConfig(bucket="apply-test", endpoint="http://127.0.0.1:9", retry_seconds=0))
    try:
        refused = await client.get(path)
        assert refused.status_code == 503 and refused.json()["code"] == "STORAGE_UNAVAILABLE"
        health = (await client.get("/api/v1/health")).json()
        assert health["storage"] is False and health["status"] == "degraded"
    finally:
        rt.files = reachable
    assert (await client.get("/api/v1/health")).json() | {"version": "-"} == {
        "status": "ok",
        "database": True,
        "storage": True,
        "version": "-",
    }
