"""
Auto over HTTP: a strong match on an Auto search is tracked, its documents written and checked, and it's Ready
for you. apply never sends it: the person does (the extension, or Mark as submitted), and that finishes the run.
Anything that needs the person first lands in Needs you with its reason.
"""

import json
from datetime import datetime

from tests.conftest import poll

from .helpers import PROFILE

FORM = "https://jobs.ashbyhq.com/acme/f3e1c2b4-1111-4111-8111-111111111111/application"
CLEAN_RESUME = "# Sam Rai\nsam@example.com\n\n### Experience\n- Backend Engineer, Himal Tech: built Django REST APIs"


def model(model_server, *, score: int = 90, warnings: bool = False, drafts: dict | None = None):
    def respond(body):
        props = body.get("format", {}).get("properties", {})
        prompt = body["messages"][0]["content"]
        if "claims" in props:
            quote = {"quote": "built Django REST APIs", "reason": "Check this."}
            return json.dumps({"claims": [quote] if warnings else []})
        if "fit_score" in props:
            return json.dumps({"fit_score": score, "reasons": ["Python fits."], "dealbreakers": []})
        if "answers" in props:
            asked = [line[2:] for line in prompt.split("<<<QUESTIONS\n", 1)[1].split("\nQUESTIONS>>>")[0].splitlines()]
            return json.dumps({"answers": [{"question": q, "answer": (drafts or {}).get(q, "")} for q in asked]})
        if "format" in body:
            return json.dumps({k: "" for k in props} | {"job_title": "Backend Engineer", "company_name": "Acme"})
        return CLEAN_RESUME if "You write resumes" in prompt else "Dear Hiring Manager,\n\nSam Rai"

    model_server.responder = respond


async def strong_match(client, model_server, worker, **settings) -> dict:
    """An Auto search, a pasted posting, scored strong: the run it starts."""
    await client.post("/api/v1/profiles", json=PROFILE)
    if settings:
        await client.patch("/api/v1/auto/settings", json=settings)
    opp = (
        await client.post("/api/v1/opportunities", json={"text": f"Backend Engineer at Acme {datetime.now()}"})
    ).json()
    await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    await client.patch(f"/api/v1/opportunities/{opp['id']}", json={"apply_url": FORM, "issuer_name": "Acme Robotics"})
    search = await client.post("/api/v1/searches", json={"name": "All", "criteria": {}, "auto_enabled": True})
    assert search.json()["auto_enabled"] is True
    await poll(client, "/api/v1/auto/counts", lambda c: c["waiting"] + c["ready"] + c["needs_you"] >= 1)
    for group in ("waiting", "ready", "needs_you"):
        items = (await client.get(f"/api/v1/auto/runs?group={group}")).json()["items"]
        if items:
            return items[0]
    raise AssertionError("no run started")


async def ready(client, run: dict) -> dict:
    return await poll(client, f"/api/v1/auto/runs/{run['id']}", lambda b: b["status"] in ("ready", "needs_you"))


async def test_a_strong_match_is_prepared_and_the_person_sends_it(client, owner, model_server, worker):
    model(model_server)
    run = await ready(client, await strong_match(client, model_server, worker))
    assert run["status"] == "ready", run
    assert run["ready_at"] and run["application_id"]
    counts = (await client.get("/api/v1/auto/counts")).json()
    assert counts == {"waiting": 0, "ready": 1, "needs_you": 0, "sent": 0}
    docs = (await client.get(f"/api/v1/applications/{run['application_id']}/documents")).json()["items"]
    assert {d["document_type"] for d in docs if d["is_active"]} == {"resume", "cover_letter"}

    # apply never sends: nothing submitted, and there's no way for anything but the person to.
    kit = (await client.get(f"/api/v1/applications/{run['application_id']}/kit")).json()
    assert kit["submissions"] == []
    assert (await client.post("/api/v1/runner/claim", json={})).status_code in (404, 405)
    assert (await client.post(f"/api/v1/auto/runs/{run['id']}/send-now")).status_code in (404, 405)

    # The person sends it (here, Mark as submitted; the extension records the same): the run is done.
    submitted = await client.post(f"/api/v1/applications/{run['application_id']}/submissions", json={})
    assert submitted.status_code in (200, 201), submitted.text
    done = (await client.get(f"/api/v1/auto/runs/{run['id']}")).json()
    assert done["status"] == "sent" and done["submission_id"] == submitted.json()["id"]
    assert (await client.get("/api/v1/auto/counts")).json()["sent"] == 1

    # Undone: not sent after all, so it's Ready for you again.
    await client.post(f"/api/v1/submissions/{submitted.json()['id']}/undo")
    again = (await client.get(f"/api/v1/auto/runs/{run['id']}")).json()
    assert again["status"] == "ready" and again["submission_id"] is None


async def test_stop_takes_it_off_ready_for_you_and_keeps_the_application(client, owner, model_server, worker):
    model(model_server)
    run = await ready(client, await strong_match(client, model_server, worker))
    stopped = await client.post(f"/api/v1/auto/runs/{run['id']}/stop")
    assert stopped.json()["status"] == "stopped"
    assert (await client.get(f"/api/v1/applications/{run['application_id']}")).status_code == 200
    again = await client.post(f"/api/v1/auto/runs/{run['id']}/stop")
    assert again.status_code == 409 and again.json()["code"] == "AUTO_ACTION_NOT_ALLOWED"


async def test_paused_auto_prepares_nothing(client, owner, model_server, worker):
    model(model_server)
    run = await strong_match(client, model_server, worker, auto_paused=True)
    found = await poll(client, f"/api/v1/auto/runs/{run['id']}", lambda b: b["status"] == "needs_you")
    assert found["reason"] == "AUTO_PAUSED" and found["application_id"] is None


async def strong_match_again(client, model_server, issuer: str = "Globex") -> dict:
    opp = (
        await client.post("/api/v1/opportunities", json={"text": f"Backend Engineer at {issuer} {datetime.now()}"})
    ).json()
    await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}",
        json={"apply_url": FORM.replace("acme", issuer.split()[0].lower()), "issuer_name": issuer},
    )
    search = (await client.get("/api/v1/searches")).json()["items"][0]
    await client.patch(f"/api/v1/searches/{search['id']}", json={"name": search["name"] + "!"})  # runs it again
    runs = await poll(
        client,
        "/api/v1/auto/runs?group=needs_you",
        lambda b: any(r["opportunity"]["id"] == opp["id"] for r in b["items"]),
    )
    return next(r for r in runs["items"] if r["opportunity"]["id"] == opp["id"])


async def test_the_same_issuer_and_the_cap(client, owner, model_server, worker):
    model(model_server)
    await ready(client, await strong_match(client, model_server, worker))
    same = await strong_match_again(client, model_server, issuer="Acme Robotics, Inc.")
    assert same["reason"] == "AUTO_SAME_ISSUER"

    await client.patch("/api/v1/auto/settings", json={"auto_daily_cap": 1})
    capped = await strong_match_again(client, model_server, issuer="Initech")
    assert capped["reason"] == "AUTO_CAP_REACHED"


async def test_claim_warnings_need_you_then_try_again(client, owner, model_server, worker):
    model(model_server, warnings=True)
    run = await strong_match(client, model_server, worker)
    found = await poll(client, f"/api/v1/auto/runs/{run['id']}", lambda b: b["status"] == "needs_you")
    assert found["reason"] == "AUTO_CLAIM_WARNINGS" and found["reason_detail"]["count"] >= 1

    # The person says "It's true" to each warning, then tries again: it's prepared.
    docs = (await client.get(f"/api/v1/applications/{found['application_id']}/documents")).json()["items"]
    for doc in docs:
        for warning in doc["claim_warnings"]:
            await client.post(
                f"/api/v1/applications/{found['application_id']}/documents/{doc['id']}/warnings/{warning['id']}",
                json={"resolution": "kept"},
            )
    again = await client.post(f"/api/v1/auto/runs/{run['id']}/retry")
    assert again.json()["status"] == "starting"
    assert (await ready(client, run))["status"] == "ready"


async def test_settings_are_the_score_the_cap_and_pause_only(client, owner):
    settings = (await client.get("/api/v1/auto/settings")).json()
    assert set(settings) == {"auto_paused", "auto_min_score", "auto_daily_cap"}
    gone = await client.patch("/api/v1/auto/settings", json={"auto_hold_hours": 2})
    assert gone.status_code == 422


async def test_no_token_can_drive_auto(client, owner, other_client, model_server, worker):
    model(model_server)
    run = await strong_match(client, model_server, worker)
    runner = await client.post(
        "/api/v1/tokens", json={"name": "Runner", "kind": "runner", "scopes": ["applications:read"]}
    )
    assert runner.status_code == 422
    scoped = await client.post("/api/v1/tokens", json={"name": "x", "kind": "extension", "scopes": ["auto:run"]})
    assert scoped.status_code == 422
    assert (await other_client.post(f"/api/v1/auto/runs/{run['id']}/stop")).status_code == 404


async def test_deleting_the_application_stops_its_run_and_its_match_is_saved_again(client, owner, model_server, worker):
    model(model_server)
    run = await strong_match(client, model_server, worker)
    run = await poll(client, f"/api/v1/auto/runs/{run['id']}", lambda r: r["application_id"] is not None)
    assert (await client.delete(f"/api/v1/applications/{run['application_id']}")).status_code == 204
    after = (await client.get(f"/api/v1/auto/runs/{run['id']}")).json()
    assert after["status"] == "stopped" and after["application_id"] is None
    matches = (await client.get("/api/v1/matches", params={"status": "saved"})).json()["items"]
    assert run["match_id"] in [m["id"] for m in matches]
