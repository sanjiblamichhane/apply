"""
The first journey, end to end over HTTP with the real worker loop and a fake model server: paste a posting, create
an application, ask for a resume, poll until it is ready. Then what people see while it works.
"""

import asyncio

from tests.conftest import poll

from .helpers import POSTING, PROFILE

RESUME = "# Sam Rai\nsam@example.com\n\n### Experience\n- Backend Engineer, Himal Tech: Django REST APIs"
# As kept: the header is the profile's, as the template has it, in place of the model's.
WRITTEN = (
    "# Sam Rai\n\nEmail: [sam@example.com](mailto:sam@example.com)\n\n"
    "### Experience\n- Backend Engineer, Himal Tech: Django REST APIs\n"
)


async def start(client) -> tuple[dict, dict]:
    profile = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    app = (
        await client.post("/api/v1/applications", json={"opportunity_id": opp["id"], "profile_id": profile["id"]})
    ).json()
    return profile, app


def writer(model_server, text=RESUME):
    import json

    def respond(body):
        if "format" in body:  # the posting being read
            return json.dumps(
                {k: "" for k in body["format"]["properties"]}
                | {"job_title": "Senior Backend Engineer", "company_name": "Acme Robotics"}
            )
        return text

    model_server.responder = respond


async def test_paste_apply_generate_and_poll_until_ready(client, owner, model_server, worker):
    writer(model_server)
    _, app = await start(client)
    queued = await client.post(f"/api/v1/applications/{app['id']}/documents", json={"document_type": "resume"})
    assert queued.status_code == 202, queued.text
    pending = queued.json()
    assert pending["status"] == "pending" and pending["version"] == 0 and not pending["is_active"]

    doc = await poll(
        client, f"/api/v1/applications/{app['id']}/documents/{pending['id']}", lambda d: d["status"] != "pending"
    )
    assert doc["status"] == "ready", doc
    assert doc["version"] == 1 and doc["is_active"] and doc["error_code"] is None
    assert doc["content_markdown"] == WRITTEN and doc["model"] == "writer:8b"
    prompt = next(p for p in model_server.prompts if "You write resumes" in p)
    assert "Himal Tech" in prompt and "Celery" in prompt
    written = next(r for r in model_server.requests if "You write resumes" in r["messages"][0]["content"])
    assert written["think"] is False and written["options"] == {"temperature": 0.4, "num_ctx": 16384}
    listed = (await client.get(f"/api/v1/applications/{app['id']}/documents")).json()["items"]
    assert [d["id"] for d in listed] == [doc["id"]]


async def test_the_version_in_use_stays_in_use_until_the_new_one_is_ready(client, owner, model_server, worker):
    writer(model_server, "# Version one")
    _, app = await start(client)
    base = f"/api/v1/applications/{app['id']}/documents"
    first = (await client.post(base, json={"document_type": "resume"})).json()
    await poll(client, f"{base}/{first['id']}", lambda d: d["status"] == "ready")

    writer(model_server, "## Version two")
    model_server.delay = 0.5
    second = (await client.post(base, json={"document_type": "resume"})).json()
    await asyncio.sleep(0.1)
    during = {d["id"]: d for d in (await client.get(base)).json()["items"]}
    assert during[first["id"]]["is_active"] and during[second["id"]]["status"] == "pending"
    assert not during[second["id"]]["is_active"] and during[second["id"]]["version"] == 0

    done = await poll(client, f"{base}/{second['id']}", lambda d: d["status"] != "pending")
    assert done["version"] == 2 and done["is_active"] and done["content_markdown"].endswith("\n\n## Version two\n")
    assert not (await client.get(f"{base}/{first['id']}")).json()["is_active"]


async def test_a_model_failure_ends_as_failed_with_a_reason_never_pending(client, owner, model_server, worker):
    writer(model_server)
    _, app = await start(client)
    model_server.status = 500
    base = f"/api/v1/applications/{app['id']}/documents"
    queued = (await client.post(base, json={"document_type": "cover_letter"})).json()
    doc = await poll(client, f"{base}/{queued['id']}", lambda d: d["status"] != "pending")
    assert doc["status"] == "failed" and doc["error_code"] == "LLM_UNREACHABLE"
    assert doc["version"] == 0 and not doc["is_active"] and doc["content_markdown"] == ""

    model_server.status = 200  # trying again works, and makes version 1
    retry = (await client.post(base, json={"document_type": "cover_letter"})).json()
    done = await poll(client, f"{base}/{retry['id']}", lambda d: d["status"] != "pending")
    assert done["status"] == "ready" and done["version"] == 1


async def test_asking_again_while_one_is_being_written_returns_that_one(client, owner, model_server):
    writer(model_server)
    _, app = await start(client)  # no worker: it stays pending
    base = f"/api/v1/applications/{app['id']}/documents"
    first = await client.post(base, json={"document_type": "resume"})
    second = await client.post(base, json={"document_type": "resume"})
    assert first.status_code == 202 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    both = await asyncio.gather(*(client.post(base, json={"document_type": "cover_letter"}) for _ in range(5)))
    assert len({r.json()["id"] for r in both}) == 1


async def test_running_the_job_twice_writes_one_version(client, owner, model_server, rt):
    from apply.libs.jobs import JobContext
    from apply.logic import documents

    writer(model_server)
    _, app = await start(client)
    base = f"/api/v1/applications/{app['id']}/documents"
    queued = (await client.post(base, json={"document_type": "resume"})).json()
    ctx = JobContext(
        id="x",
        kind="document.generate",
        payload={"document_id": queued["id"]},
        attempt=1,
        max_attempts=3,
        owner_id=None,
    )
    await asyncio.gather(documents.write(rt, ctx), documents.write(rt, ctx))
    items = (await client.get(base)).json()["items"]
    assert [(d["status"], d["version"]) for d in items] == [("ready", 1)]


async def test_a_worker_that_dies_on_the_last_try_still_ends_the_document(client, owner, model_server, rt):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from apply.store.sql.models import jobs
    from apply.worker import build

    writer(model_server)
    _, app = await start(client)
    base = f"/api/v1/applications/{app['id']}/documents"
    queued = (await client.post(base, json={"document_type": "resume"})).json()
    async with rt.db.engine.begin() as conn:  # as if a worker took it on its last attempt and died
        await conn.execute(
            update(jobs)
            .where(jobs.c.kind == "document.generate")
            .values(
                status="running", attempts=3, locked_by="dead", locked_until=datetime.now(UTC) - timedelta(seconds=1)
            )
        )
    await build(rt, queues=["llm"], concurrency=1).run_until_idle()
    doc = (await client.get(f"{base}/{queued['id']}")).json()
    assert doc["status"] == "failed" and doc["error_code"] == "INTERNAL"


async def test_what_cannot_be_written(client, owner, model_server):
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    base = f"/api/v1/applications/{app['id']}/documents"
    no_profile = await client.post(base, json={"document_type": "resume"})
    assert no_profile.status_code == 422 and no_profile.json()["code"] == "PROFILE_REQUIRED"
    await client.post("/api/v1/profiles", json=PROFILE)
    not_written = await client.post(base, json={"document_type": "job_description"})
    assert not_written.json()["code"] == "DOCUMENT_TYPE_NOT_GENERATABLE"
    unknown = await client.post(base, json={"document_type": "haiku"})
    assert unknown.status_code == 404 and unknown.json()["code"] == "DOCUMENT_TYPE_NOT_FOUND"


async def test_another_account_cannot_see_or_ask_for_documents(client, owner, other_client, model_server):
    _, app = await start(client)
    base = f"/api/v1/applications/{app['id']}/documents"
    doc = (await client.post(base, json={"document_type": "resume"})).json()
    assert (await other_client.get(base)).status_code == 404
    assert (await other_client.get(f"{base}/{doc['id']}")).status_code == 404
    assert (await other_client.post(base, json={"document_type": "resume"})).status_code == 404


async def test_cards_say_what_each_document_is_doing(client, owner, model_server, worker):
    writer(model_server)
    _, app = await start(client)
    base = f"/api/v1/applications/{app['id']}/documents"
    resume = (await client.post(base, json={"document_type": "resume"})).json()
    await poll(client, f"{base}/{resume['id']}", lambda d: d["status"] == "ready")
    model_server.status = 500
    letter = (await client.post(base, json={"document_type": "cover_letter"})).json()
    await poll(client, f"{base}/{letter['id']}", lambda d: d["status"] == "failed")

    [card] = (await client.get("/api/v1/applications")).json()["items"]
    states = {(d["document_type"], d["status"]) for d in card["current_documents"]}
    assert states == {("resume", "ready"), ("cover_letter", "failed")}
    assert card["opportunity"]["extraction"]["status"] in ("pending", "ready", "manual")
