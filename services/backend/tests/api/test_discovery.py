"""
Discovery, end to end over HTTP with the real worker and a fake model: sources and a search fill a
ranked inbox, and fetching again, or the same job on another board, adds no duplicates.
"""

import json

from tests.conftest import poll
from tests.support.boards import BOARD01, BOARD02, BOARD03, CONTRACTS_FINDER, serve

from .helpers import PROFILE


def scorer(model_server, scores: dict[str, int]):
    """A model that scores by the job title in the prompt (and writes nothing else)."""

    def respond(body):
        prompt = body["messages"][0]["content"]
        title = next((t for t in scores if f"Title: {t}\n" in prompt), None)
        return json.dumps({"fit_score": scores.get(title, 40), "reasons": [f"Fits {title}"], "dealbreakers": []})

    model_server.responder = respond


async def settled(client, expected: int):
    return await poll(
        client,
        "/api/v1/matches",
        lambda b: len(b["items"]) >= expected and all(m["score_status"] != "pending" for m in b["items"]),
        within=60,
    )


async def test_sources_and_a_search_fill_a_ranked_inbox_without_duplicates(client, owner, site, model_server, worker):
    for boards in (BOARD01, BOARD02, BOARD03):
        serve(site, boards)
    scorer(model_server, {"Senior Backend Engineer": 88, "Backend Engineer (Python)": 72, "Data Analyst": 55})
    await client.post("/api/v1/profiles", json=PROFILE)

    for kind, config in (
        ("board01", {"board": "acme"}),
        ("board02", {"company": "himal", "display": "Himal Tech"}),
        ("board03", {"board": "example-analytics", "company": "Example Analytics"}),
        ("board03", {"board": "acme", "company": "Acme Robotics"}),
    ):
        made = await client.post("/api/v1/sources", json={"kind": kind, "config": config})
        assert made.status_code == 201, made.text
    search = await client.post(
        "/api/v1/searches",
        json={"name": "Python work", "criteria": {"keywords": ["python", "sql"], "exclude": ["designer"]}},
    )
    assert search.status_code == 201, search.text

    inbox = await settled(client, 3)
    titles = [(m["opportunity"]["title"], m["score"]) for m in inbox["items"]]
    # Best first; the two boards' copies of the Acme job are one match; the designer and the Go
    # role (no python, no sql) don't pass the rules.
    assert titles == [("Senior Backend Engineer", 88), ("Backend Engineer (Python)", 72), ("Data Analyst", 55)]
    assert inbox["counts"]["new"] == 3
    first = inbox["items"][0]
    assert first["score_reasons"] == ["Fits Senior Backend Engineer"] and first["search_ids"] == [search.json()["id"]]
    assert first["prefilter"]["keywords"] == ["python"]
    scoring = [r for r in model_server.requests if "format" in r and "fit_score" in json.dumps(r["format"])]
    assert all(r["options"]["temperature"] == 0.0 for r in scoring) and len(scoring) == 3

    # Fetch every source again: nothing new.
    from sqlalchemy import update

    from apply.logic import scheduler
    from apply.store.sql.models import Source

    async with worker.queue.engine.begin() as conn:
        await conn.execute(update(Source).values(last_fetched_at=None))
    await scheduler.tick(owner_rt(client))
    await poll(client, "/api/v1/sources", lambda b: all(s["last_status"] == "ok" for s in b["items"]))
    again = await settled(client, 3)
    assert len(again["items"]) == 3 and len(scoring) == 3


def owner_rt(client):
    return client._transport.app.state.runtime  # the app's runtime, for the scheduler


async def test_a_posting_that_goes_away_is_closed(client, owner, site, model_server, worker, rt):
    serve(site, BOARD01)
    scorer(model_server, {})
    await client.post("/api/v1/profiles", json=PROFILE)
    source = (await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})).json()
    await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})
    await settled(client, 2)

    site.add(
        "/v1/boards/acme/jobs",
        json.dumps({"jobs": [BOARD01["/v1/boards/acme/jobs"]["jobs"][1]]}),
        content_type="application/json",
    )
    from sqlalchemy import update

    from apply.logic import scheduler
    from apply.store.sql.models import Source

    async with rt.db.engine.begin() as conn:
        await conn.execute(update(Source).where(Source.id == source["id"]).values(last_fetched_at=None))
    await scheduler.tick(rt)
    inbox = await poll(
        client, "/api/v1/matches", lambda b: any(m["opportunity"]["status"] == "closed" for m in b["items"])
    )
    closed = {m["opportunity"]["title"]: m["opportunity"]["status"] for m in inbox["items"]}
    assert closed == {"Senior Backend Engineer": "closed", "Product Designer": "open"}


async def test_track_dismiss_and_undo(client, owner, site, model_server, worker):
    serve(site, BOARD01)
    scorer(model_server, {"Senior Backend Engineer": 90, "Product Designer": 30})
    await client.post("/api/v1/profiles", json=PROFILE)
    await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})
    await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})
    inbox = await settled(client, 2)
    best, worst = inbox["items"]

    tracked = await client.post(f"/api/v1/matches/{best['id']}/track")
    assert tracked.status_code == 200
    application_id = tracked.json()["application_id"]
    app = (await client.get(f"/api/v1/applications/{application_id}")).json()
    assert app["opportunity"]["id"] == best["opportunity"]["id"] and app["stage"]["code"] == "new"
    again = await client.post(f"/api/v1/matches/{best['id']}/track")
    assert again.json()["application_id"] == application_id  # no second application

    dismissed = await client.patch(f"/api/v1/matches/{worst['id']}", json={"status": "dismissed"})
    assert dismissed.json()["status"] == "dismissed"
    inbox = (await client.get("/api/v1/matches")).json()
    assert inbox["items"] == [] and inbox["counts"] == {"new": 0, "saved": 0, "dismissed": 1, "tracked": 1}
    undone = await client.patch(f"/api/v1/matches/{worst['id']}", json={"status": "new"})
    assert undone.json()["status"] == "new"
    assert [m["id"] for m in (await client.get("/api/v1/matches")).json()["items"]] == [worst["id"]]
    tracked_list = (await client.get("/api/v1/matches", params={"status": "tracked"})).json()
    assert [m["application_id"] for m in tracked_list["items"]] == [application_id]


async def test_a_model_that_fails_leaves_matches_unscored_not_guessed(client, owner, site, model_server, worker):
    serve(site, BOARD01)
    model_server.status = 500
    await client.post("/api/v1/profiles", json=PROFILE)
    await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})
    await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})
    inbox = await settled(client, 2)
    assert {(m["score"], m["score_status"], m["score_error_code"]) for m in inbox["items"]} == {
        (None, "failed", "LLM_UNREACHABLE")
    }


async def test_needing_sponsorship_flags_postings_that_wont(client, owner, site, model_server, worker):
    serve(site, BOARD01)
    scorer(model_server, {"Senior Backend Engineer": 92})
    await client.post("/api/v1/profiles", json=PROFILE)
    await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})
    await client.post(
        "/api/v1/searches", json={"name": "Visa", "criteria": {"keywords": ["python"], "needs_sponsorship": True}}
    )
    [match] = (await settled(client, 1))["items"]
    assert match["dealbreakers"][0]["code"] == "NO_SPONSORSHIP"


async def test_the_daily_cap_holds_scores_over(client, owner, site, model_server, rt):
    rt.settings.score_daily_cap = 1
    serve(site, BOARD01)
    scorer(model_server, {})
    await client.post("/api/v1/profiles", json=PROFILE)
    await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})
    await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})
    from apply.worker import build

    await build(rt, queues=["llm", "default"], concurrency=1, schedule=False).run_until_idle()
    items = (await client.get("/api/v1/matches")).json()["items"]
    assert sorted(m["score_status"] for m in items) == ["capped", "scored"]
    capped = next(m for m in items if m["score_status"] == "capped")
    assert capped["score"] is None and capped["score_error_code"] == "SCORE_CAP_REACHED"


async def test_sources_respect_their_terms(client, owner, site, worker):
    serve(site, CONTRACTS_FINDER)
    source = (
        await client.post(
            "/api/v1/sources",
            json={"pack": "tender", "kind": "contracts_finder", "config": {"keyword": "software"}, "interval_hours": 1},
        )
    ).json()
    assert source["interval_hours"] == 6  # its terms ask for no more than 4 a day
    await poll(client, f"/api/v1/sources/{source['id']}", lambda b: b["last_status"] == "ok")
    too_soon = await client.post(f"/api/v1/sources/{source['id']}/fetch")
    assert too_soon.status_code == 409 and too_soon.json()["code"] == "SOURCE_TOO_SOON"
    kinds = (await client.get("/api/v1/source-kinds?pack=tender")).json()["items"]
    tenders = next(k for k in kinds if k["kind"] == "contracts_finder")
    assert "Open Government Licence" in tenders["attribution"]
    bad = await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "../x"}})
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_ATTRIBUTES"


async def test_a_failing_source_says_why(client, owner, site, worker):
    site.add("/v1/boards/gone", "nope", status=404)
    source = (
        await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "gone", "company": "Gone"}})
    ).json()
    done = await poll(client, f"/api/v1/sources/{source['id']}", lambda b: b["last_status"] != "never")
    assert done["last_status"] == "failed" and done["last_error_code"] == "FETCH_FAILED"


async def test_the_briefing(client, owner, site, model_server, worker):
    serve(site, BOARD01)
    scorer(model_server, {"Senior Backend Engineer": 88})
    await client.post("/api/v1/profiles", json=PROFILE)
    await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})
    await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})
    await settled(client, 2)
    # At the owner's briefing hour the worker's scheduler builds it on its own.
    await client.patch("/api/v1/auth/me", json={"time_zone": "UTC", "briefing_hour": 0})
    await poll(client, "/api/v1/briefings/today", lambda b: b is not None)
    briefing = (await client.post("/api/v1/briefings/today")).json()  # and again, now
    assert briefing["content"]["new_matches"]["count"] == 2
    assert briefing["content"]["new_matches"]["top"][0]["title"] == "Senior Backend Engineer"
    assert (await client.get("/api/v1/briefings/today")).json()["date"] == briefing["date"]
    me = await client.patch("/api/v1/auth/me", json={"time_zone": "Asia/Kathmandu", "briefing_hour": 6})
    assert me.json()["time_zone"] == "Asia/Kathmandu" and me.json()["briefing_hour"] == 6
    assert (await client.patch("/api/v1/auth/me", json={"time_zone": "Mars/Olympus"})).status_code == 422


async def test_another_account_sees_none_of_it(client, owner, other_client, site, model_server, worker):
    serve(site, BOARD01)
    await client.post("/api/v1/profiles", json=PROFILE)
    source = (await client.post("/api/v1/sources", json={"kind": "board01", "config": {"board": "acme"}})).json()
    search = (await client.post("/api/v1/searches", json={"name": "All", "criteria": {}})).json()
    [match, _] = (await settled(client, 2))["items"]
    for call in (
        other_client.get(f"/api/v1/sources/{source['id']}"),
        other_client.get(f"/api/v1/searches/{search['id']}"),
        other_client.patch(f"/api/v1/matches/{match['id']}", json={"status": "dismissed"}),
        other_client.post(f"/api/v1/matches/{match['id']}/track"),
    ):
        assert (await call).status_code == 404
    assert (await other_client.get("/api/v1/matches")).json()["items"] == []
    bad = await other_client.post("/api/v1/searches", json={"name": "x", "criteria": {"source_ids": [source["id"]]}})
    assert bad.status_code == 404


async def test_a_company_board_is_recognised_from_its_address(client, owner):
    found = await client.post("/api/v1/sources/recognise", json={"url": "https://jobs.lever.co/himal/some-job"})
    assert found.status_code == 200, found.text
    assert found.json() == {"kind": "board02", "config": {"company": "himal"}}
    workday = await client.post(
        "/api/v1/sources/recognise", json={"url": "https://acme.wd5.myworkdayjobs.com/External?q=x"}
    )
    assert workday.json() == {
        "kind": "board04",
        "config": {"careers_url": "https://acme.wd5.myworkdayjobs.com/External"},
    }
    unknown = await client.post("/api/v1/sources/recognise", json={"url": "https://example.com/careers"})
    assert unknown.status_code == 422 and unknown.json()["code"] == "SOURCE_NOT_RECOGNISED"
    kinds = (await client.get("/api/v1/source-kinds")).json()["items"]
    assert kinds and all(k["from_address"] for k in kinds)  # every job source is a company's board
    tenders = (await client.get("/api/v1/source-kinds?pack=tender")).json()["items"]
    assert not any(k["from_address"] for k in tenders)
