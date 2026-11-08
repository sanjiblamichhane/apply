"""
The extension over HTTP: personal API tokens and what the browser extension does with one. It finds the application
for the form it's on, reads the fill sheet, records the submission from the board's confirmation page, and
undoes it. A token reaches only the routes that accept its scopes.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import update

from apply.logic.auth import hash_token
from apply.store.sql.models import ApiToken
from tests.conftest import TEST_API, poll

from .helpers import EXTRACTED, PROFILE, ld_page
from .test_review_and_kit import model

ALL = ["applications:read", "applications:write", "submissions:write"]
FORM_URL = "https://jobs.lever.co/himal/a1b2c3d4-0000-4000-8000-000000000001/apply"
POSTING_URL = "https://jobs.lever.co/himal/a1b2c3d4-0000-4000-8000-000000000001"


@asynccontextmanager
async def extension(client: httpx.AsyncClient, secret: str | None):
    """Another client on the same app, as the extension is: no cookies, only the token."""
    headers = {"Authorization": f"Bearer {secret}", "Origin": "chrome-extension://abcdefghijklmnop"} if secret else {}
    transport = httpx.ASGITransport(app=client._transport.app)  # type: ignore[attr-defined]
    async with httpx.AsyncClient(transport=transport, base_url=TEST_API, headers=headers) as c:
        yield c


async def make_token(client, scopes=ALL, **extra) -> dict:
    made = await client.post("/api/v1/tokens", json={"name": "Browser on the laptop", "scopes": scopes, **extra})
    assert made.status_code == 201, made.text
    return made.json()


async def tracked(client, model_server, worker) -> tuple[str, str]:
    """An application for a board02 posting with a written resume: (application id, document id)."""
    model(model_server)
    profile = {
        **PROFILE,
        "attributes": {
            **PROFILE["attributes"],
            "phone": "+977 980 000 0000",
            "links": [{"label": "", "url": "https://www.linkedin.com/in/example"}],
        },
    }
    await client.post("/api/v1/profiles", json=profile)
    opp = (await client.post("/api/v1/opportunities", json={"url": POSTING_URL, "html": page()})).json()
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    base = f"/api/v1/applications/{app['id']}/documents"
    doc = (await client.post(base, json={"document_type": "resume"})).json()
    await poll(client, f"{base}/{doc['id']}", lambda d: d["status"] == "ready" and d["claims_status"] != "pending")
    return app["id"], doc["id"]


def page() -> str:
    return ld_page(
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Backend Engineer (Python)",
            "hiringOrganization": {"@type": "Organization", "name": "Himal"},
            "description": "<p>Design Django APIs and own Postgres.</p>",
            "datePosted": "2026-10-20",
        }
    )


async def test_a_token_is_shown_once_and_kept_as_a_hash(client, owner, rt):
    made = await make_token(client)
    secret = made["secret"]
    assert secret.startswith("apl_") and len(secret) > 40
    assert made["token"]["prefix"] == secret[:12] and made["token"]["scopes"] == ALL
    assert made["token"]["expires_at"] is not None  # 90 days unless chosen otherwise
    listed = (await client.get("/api/v1/tokens")).json()["items"]
    assert [t["id"] for t in listed] == [made["token"]["id"]]
    assert secret not in str(listed)
    async with rt.db.transaction() as session:
        row = await session.get(ApiToken, made["token"]["id"])
        assert row.token_hash == hash_token(secret) and secret not in str(row.__dict__)

    forever = await make_token(client, ["applications:read"], expires_in_days=None)
    assert forever["token"]["expires_at"] is None
    bad = await client.post("/api/v1/tokens", json={"name": "x", "scopes": ["profiles:write"]})
    assert bad.status_code == 422


async def test_a_token_reaches_only_what_its_scopes_allow(client, owner):
    read_only = (await make_token(client, ["applications:read"]))["secret"]
    async with extension(client, read_only) as ext:
        me = await ext.get("/api/v1/tokens/current")
        assert me.status_code == 200 and me.json()["email"] == owner["email"]
        assert me.json()["token"]["scopes"] == ["applications:read"]
        assert "web_url" in me.json()  # the first allowed origin (none in these tests)
        stages = (await ext.get("/api/v1/packs/job")).json()["pipeline"]["stages"]
        assert "in_progress" in [stage["code"] for stage in stages]
        assert (await ext.get(f"/api/v1/applications/by-url?url={POSTING_URL}")).json()["code"] == (
            "OPPORTUNITY_NOT_FOUND"
        )

        missing = await ext.post("/api/v1/opportunities", json={"text": "Engineer at Acme"})
        assert missing.status_code == 403 and missing.json()["code"] == "TOKEN_SCOPE_MISSING"
        assert missing.json()["scope"] == "applications:write"

        # Routes that don't take tokens at all: the profile, the account, exports, and tokens themselves.
        for call in (
            ext.get("/api/v1/profiles"),
            ext.get("/api/v1/auth/me"),
            ext.get("/api/v1/tokens"),
            ext.post("/api/v1/tokens", json={"name": "more", "scopes": ALL}),
            ext.patch("/api/v1/auth/me", json={"locale": "ne"}),
        ):
            response = await call
            assert response.status_code == 403 and response.json()["code"] == "TOKEN_NOT_ALLOWED", response.text

    async with extension(client, "apl_" + "x" * 43) as ext:
        unknown = await ext.get("/api/v1/tokens/current")
        assert unknown.status_code == 401 and unknown.json()["code"] == "TOKEN_INVALID"


async def test_revoked_and_expired_tokens_stop_working(client, owner, rt):
    made = await make_token(client)
    async with extension(client, made["secret"]) as ext:
        assert (await ext.get("/api/v1/tokens/current")).status_code == 200
        revoked = await client.delete(f"/api/v1/tokens/{made['token']['id']}")
        assert revoked.status_code == 200 and revoked.json()["revoked_at"] is not None
        assert (await ext.get("/api/v1/tokens/current")).json()["code"] == "TOKEN_INVALID"

    other = await make_token(client)
    async with rt.db.transaction() as session:
        await session.execute(
            update(ApiToken)
            .where(ApiToken.id == other["token"]["id"])
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
    async with extension(client, other["secret"]) as ext:
        assert (await ext.get("/api/v1/tokens/current")).status_code == 401
    listed = (await client.get("/api/v1/tokens")).json()["items"]
    assert len(listed) == 2  # a revoked token stays listed


async def test_origin_checks_still_guard_the_session(client, owner):
    """A token isn't sent by the browser on its own, so it skips the Origin check; a cookie never does."""
    secret = (await make_token(client))["secret"]
    async with extension(client, secret) as ext:
        made = await ext.post("/api/v1/opportunities", json={"text": "Engineer at Acme\nPython"})
        assert made.status_code == 201  # from chrome-extension://…
    cross = await client.post(
        "/api/v1/opportunities", json={"text": "Engineer at Evil"}, headers={"Origin": "https://evil.example"}
    )
    assert cross.status_code == 403 and cross.json()["code"] == "ORIGIN_NOT_ALLOWED"
    # A made-up bearer header beside the cookie doesn't get around it either: the token alone counts.
    sneaky = await client.post(
        "/api/v1/tokens",
        json={"name": "x", "scopes": ALL},
        headers={"Origin": "https://evil.example", "Authorization": f"Bearer {secret}"},
    )
    assert sneaky.status_code == 403 and sneaky.json()["code"] == "TOKEN_NOT_ALLOWED"


async def test_the_extension_finds_fills_and_records(client, owner, model_server, worker):
    app_id, doc_id = await tracked(client, model_server, worker)
    secret = (await make_token(client))["secret"]
    async with extension(client, secret) as ext:
        # The form's own URL and the posting's both find it.
        for urls in (
            [FORM_URL, POSTING_URL],
            [POSTING_URL.replace("jobs.lever.co", "JOBS.lever.co") + "?utm_source=x"],
            [POSTING_URL + "/"],
        ):
            query = "&".join(f"url={u}" for u in urls)
            found = await ext.get(f"/api/v1/applications/by-url?{query}")
            assert found.status_code == 200, (urls, found.text)
            assert found.json()["application"]["id"] == app_id
        assert (await ext.get("/api/v1/applications/by-url?url=javascript:alert(1)")).status_code == 404

        sheet = (await ext.get(f"/api/v1/applications/{app_id}/fill")).json()
        assert sheet["values"] == {
            "full_name": "Sam Rai",
            "first_name": "Sam",
            "last_name": "Rai",
            "email": "sam@example.com",
            "phone": "+977 980 000 0000",
            "linkedin": "https://www.linkedin.com/in/example",
            "current_company": "Himal Tech",
            "current_title": "Backend Engineer",
            "past_employers": "Himal Tech",
        }
        keys = {a["key"]: a for a in sheet["answers"]}
        assert keys["gender"]["is_sensitive"] and keys["gender"]["answer"] == "decline"
        [resume] = sheet["documents"]
        assert resume["document_id"] == doc_id and resume["filename"] == "Sam Rai – Resume.pdf"
        assert not resume["reviewed"] and resume["open_warnings"] >= 1
        for _ in range(200):
            pdf = await ext.get(resume["pdf_path"])
            if pdf.status_code == 200:
                break
        assert pdf.content.startswith(b"%PDF-")

        filled = {"fields": 9, "files": ["resume"], "left_blank": ["Why do you want to work at Himal?"]}
        body = {"confirmation_url": POSTING_URL + "/thanks", "filled": filled}
        first = await ext.post(f"/api/v1/applications/{app_id}/submissions", json=body)
        assert first.status_code == 201, first.text
        record = first.json()
        assert record["channel"] == "extension"
        assert record["details"] == {"confirmation_url": POSTING_URL + "/thanks", "filled": filled}
        again = await ext.post(f"/api/v1/applications/{app_id}/submissions", json=body)
        assert again.status_code == 200 and again.json()["id"] == record["id"]  # a reloaded "thank you" page

    app = (await client.get(f"/api/v1/applications/{app_id}")).json()
    assert app["stage"]["code"] == "in_progress" and app["submitted_at"] is not None
    kit = (await client.get(f"/api/v1/applications/{app_id}/kit")).json()
    assert [s["channel"] for s in kit["submissions"]] == ["extension"]

    async with extension(client, secret) as ext:
        undone = await ext.post(f"/api/v1/submissions/{record['id']}/undo")
        assert undone.status_code == 200 and undone.json()["undone_at"] is not None
    app = (await client.get(f"/api/v1/applications/{app_id}")).json()
    assert app["stage"]["code"] == "new" and app["submitted_at"] is None


async def test_track_this_job_from_the_page_the_browser_shows(client, owner, model_server, worker):
    """ "Track this job": the page comes from the browser, so nothing is fetched (board03 draws its forms by script)."""
    secret = (await make_token(client))["secret"]
    async with extension(client, secret) as ext:
        opp = await ext.post("/api/v1/opportunities", json={"url": POSTING_URL, "html": page()})
        assert opp.status_code == 201 and opp.json()["title"] == "Backend Engineer (Python)"
        assert opp.json()["extraction"]["method"] == "json_ld"
        app = await ext.post("/api/v1/applications", json={"opportunity_id": opp.json()["id"]})
        assert app.status_code == 201
        found = await ext.get(f"/api/v1/applications/by-url?url={FORM_URL}&url={POSTING_URL}")
        assert found.json()["application"]["id"] == app.json()["id"]
    assert EXTRACTED  # the model isn't asked: the page had JSON-LD


async def test_one_owners_token_is_nothing_to_another(client, owner, other_client, model_server, worker):
    app_id, _ = await tracked(client, model_server, worker)
    mine = await make_token(client)
    theirs = (await make_token(other_client))["secret"]
    assert (await other_client.delete(f"/api/v1/tokens/{mine['token']['id']}")).json()["code"] == "TOKEN_NOT_FOUND"
    async with extension(client, theirs) as ext:
        assert (await ext.get(f"/api/v1/applications/{app_id}/fill")).status_code == 404
        assert (await ext.get(f"/api/v1/applications/by-url?url={POSTING_URL}")).status_code == 404
        assert (await ext.post(f"/api/v1/applications/{app_id}/submissions", json={})).status_code == 404
        assert (await ext.get(f"/api/v1/applications/{app_id}/documents")).status_code == 404
        assert (
            await ext.post(f"/api/v1/applications/{app_id}/documents", json={"document_type": "resume"})
        ).status_code == 404


AGENT = ["applications:read", "applications:write", "profiles:read"]


async def test_an_agent_token_reads_and_drafts_but_never_records_a_submission(client, owner, model_server, worker):
    """`apply mcp`'s token: what an AI agent may do. apply drafts and fills; the person submits."""
    app_id, doc_id = await tracked(client, model_server, worker)
    refused = await client.post(
        "/api/v1/tokens", json={"name": "Claude", "kind": "agent", "scopes": [*AGENT, "submissions:write"]}
    )
    assert refused.status_code == 422 and refused.json()["code"] == "VALIDATION_FAILED"
    made = await make_token(client, AGENT, kind="agent", name="Claude")
    assert made["token"]["kind"] == "agent" and made["token"]["scopes"] == AGENT
    async with extension(client, made["secret"]) as agent:
        listed = (await agent.get("/api/v1/applications")).json()["items"]
        assert [a["id"] for a in listed] == [app_id]
        base = f"/api/v1/applications/{app_id}/documents"
        assert [d["id"] for d in (await agent.get(base)).json()["items"]] == [doc_id]
        assert (await agent.get(f"{base}/{doc_id}")).json()["content_markdown"]
        assert (await agent.get("/api/v1/copy-sheet")).status_code == 200

        drafted = await agent.post(base, json={"document_type": "cover_letter"})
        assert drafted.status_code == 202 and drafted.json()["status"] == "pending", drafted.text
        await poll(agent, f"{base}/{drafted.json()['id']}", lambda d: d["status"] != "pending")

        body = {"confirmation_url": POSTING_URL + "/thanks", "filled": {}}
        submitted = await agent.post(f"/api/v1/applications/{app_id}/submissions", json=body)
        assert submitted.status_code == 403 and submitted.json()["code"] == "TOKEN_SCOPE_MISSING"
        for call in (
            agent.patch(f"/api/v1/applications/{app_id}", json={"notes": "x"}),
            agent.delete(f"/api/v1/applications/{app_id}"),
            agent.post(f"/api/v1/applications/{app_id}/stage", json={"stage_code": "in_progress"}),
            agent.get("/api/v1/profiles"),
            agent.post("/api/v1/tokens", json={"name": "more", "kind": "agent", "scopes": AGENT}),
        ):
            response = await call
            assert response.status_code == 403 and response.json()["code"] == "TOKEN_NOT_ALLOWED", response.text
    app = (await client.get(f"/api/v1/applications/{app_id}")).json()
    assert app["submitted_at"] is None and app["notes"] == ""
