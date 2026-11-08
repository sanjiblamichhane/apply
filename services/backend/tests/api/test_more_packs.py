"""
More packs, over HTTP with the real worker and a fake model: the tender, grant and contract packs go
end to end through the same engine the job pack uses. A profile, a pasted notice the model reads, an application
in the pack's own pipeline, both documents written and checked, the PDF, the kit and a submission, the stages;
and, for tenders and grants, discovery from the recorded Contracts Finder and Grants.gov answers.
"""

import json

import pytest

from tests.conftest import poll
from tests.support.boards import CONTRACTS_FINDER, GRANTS_GOV, serve

from .test_review_and_kit import poll_pdf

TENDER_PROFILE = {
    "pack": "tender",
    "kind": "organisation",
    "name": "Example Software",
    "summary": "A software company building case management systems for councils.",
    "attributes": {
        "legal_name": "Example Software Ltd",
        "registration_numbers": ["Company 09876543"],
        "sectors": ["Local government"],
        "capabilities": ["Hosted case management", "Data migration from legacy systems"],
        "certifications": ["ISO 27001"],
        "past_performance": [
            {
                "client": "Example Borough Council",
                "title": "Adult social care case system",
                "year": "2024",
                "value": "£180,000",
                "outcome": "Live in 9 months",
            }
        ],
        "team": [{"name": "Asha Gurung", "role": "Delivery lead", "experience": "12 years in public sector IT"}],
    },
}
TENDER_NOTICE = """Example City Council invites tenders for case management software for children's services.
Reference ECC-2026-0142. Estimated value £250,000. Closing 30 November 2026.
Suppliers must hold Cyber Essentials Plus."""
TENDER_READ = {
    "title": "Case management software for children's services",
    "buyer": "Example City Council",
    "reference": "ECC-2026-0142",
    "description_markdown": "A hosted case management system. Must meet Cyber Essentials Plus.",
    "estimated_value": "£250,000",
    "closing_date": "2026-11-30",
}

GRANT_PROFILE = {
    "pack": "grant",
    "kind": "organisation",
    "name": "Hill Clinics",
    "summary": "A rural nonprofit running mobile health clinics.",
    "attributes": {
        "legal_name": "Hill Clinics Inc",
        "mission": "Bring primary care to rural families.",
        "location": "Asheville, NC",
        "programmes": [
            {"name": "Mobile clinics", "description": "Two vans", "beneficiaries": "rural families", "results": ""}
        ],
        "past_grants": [{"funder": "Example Foundation", "title": "Vans", "year": "2023", "amount": "$90,000"}],
    },
}
GRANT_NOTICE = """Rural Health Network Development Program, EXH-27-011, from the Example Health Agency.
Awards up to $300,000. Applications close 15 January 2027. For rural nonprofits."""
GRANT_READ = {
    "title": "Rural Health Network Development Program",
    "funder": "Example Health Agency",
    "number": "EXH-27-011",
    "description_markdown": "Supports rural health networks.",
    "award_ceiling": "$300,000",
}

CONTRACT_PROFILE = {
    "pack": "contract",
    "kind": "individual",
    "name": "Freelance",
    "summary": "Freelance data engineer.",
    "attributes": {
        "business_name": "Rai Data",
        "services": [{"name": "Data pipelines", "description": "dbt and Airflow", "rate": "£600 a day"}],
        "skills": ["dbt", "Airflow", "PostgreSQL"],
    },
}
CONTRACT_BRIEF = """Kathmandu Coffee wants a freelance data engineer to move their sales reporting to dbt.
Budget about £6,000, four weeks, remote."""
CONTRACT_READ = {
    "title": "Move sales reporting to dbt",
    "client": "Kathmandu Coffee",
    "budget": "£6,000",
    "duration": "Four weeks",
    "workplace": "remote",
}

# The first line of each pack's writing prompt, and what the fake model writes for it.
WRITTEN = {
    "You write capability statements": "# Example Software Ltd\n\nWe built Example Borough Council's case system.\n\n"
    "Insurance: [CONFIRM: insurance cover]",
    "You write tender responses": "# Response to ECC-2026-0142\n\nWe hold ISO 27001 and Cyber Essentials Plus.",
    "You write letters of inquiry": "Dear Programme Officer,\n\nHill Clinics Inc runs two mobile clinics.",
    "You write project narratives": "## Need\n\nRural families wait weeks for care. We serve 4,000 people.",
    "You write proposals": "# Proposal for Kathmandu Coffee\n\nRai Data builds dbt pipelines.",
    "You write statements of work": "# Statement of work\n\nDeliverables: dbt models for sales.",
}
UNSUPPORTED = {
    "tender": "Cyber Essentials Plus",
    "grant": "We serve 4,000 people",
    "contract": "",
}


def model(model_server, read: dict, *, scores: dict[str, int] | None = None, unsupported: str = ""):
    """A model that reads notices into ``read``, scores by title, writes by prompt, and flags ``unsupported``."""

    def respond(body):
        prompt = body["messages"][0]["content"]
        schema = body.get("format") or {}
        props = schema.get("properties", {})
        if "claims" in props:
            claims = [{"quote": unsupported, "reason": "The profile doesn't say so."}] if unsupported else []
            return json.dumps({"claims": claims})
        if "fit_score" in props:
            title = next((t for t in scores or {} if f"Title: {t}\n" in prompt), None)
            return json.dumps({"fit_score": (scores or {}).get(title, 40), "reasons": ["Fits"], "dealbreakers": []})
        if props:
            return json.dumps({k: "" for k in props} | {k: v for k, v in read.items() if k in props})
        return next((text for start, text in WRITTEN.items() if prompt.startswith(start)), "Written.")

    model_server.responder = respond


async def write(client, app_id: str, document_type: str) -> dict:
    base = f"/api/v1/applications/{app_id}/documents"
    queued = await client.post(base, json={"document_type": document_type})
    assert queued.status_code == 202, queued.text
    return await poll(
        client,
        f"{base}/{queued.json()['id']}",
        lambda d: d["status"] != "pending" and d["claims_status"] != "pending",
    )


CASES = {
    "tender": (TENDER_PROFILE, TENDER_NOTICE, TENDER_READ, ("capability_statement", "tender_response")),
    "grant": (GRANT_PROFILE, GRANT_NOTICE, GRANT_READ, ("letter_of_inquiry", "project_narrative")),
    "contract": (CONTRACT_PROFILE, CONTRACT_BRIEF, CONTRACT_READ, ("proposal", "statement_of_work")),
}
STAGES = {
    "tender": ("identified", "submitted", ["clarification", "awarded"]),
    "grant": ("prospect", "submitted", ["under_review", "awarded"]),
    "contract": ("lead", "proposal_sent", ["negotiating", "won"]),
}


@pytest.mark.parametrize("pack", list(CASES))
async def test_a_pack_end_to_end_through_the_same_engine(pack, client, owner, model_server, worker):
    profile_in, notice, read, (first_doc, second_doc) = CASES[pack]
    model(model_server, read, unsupported=UNSUPPORTED[pack])
    first_stage, submitted_stage, later = STAGES[pack]

    profile = await client.post("/api/v1/profiles", json=profile_in)
    assert profile.status_code == 201, profile.text
    assert profile.json()["is_default"]
    bad = await client.post("/api/v1/profiles", json={**profile_in, "attributes": {"favourite_colour": "blue"}})
    assert bad.status_code == 422

    # Paste the notice: the model reads it into the pack's own fields.
    pasted = await client.post("/api/v1/opportunities", json={"pack": pack, "text": notice})
    assert pasted.status_code == 201, pasted.text
    opp = await poll(
        client, f"/api/v1/opportunities/{pasted.json()['id']}", lambda o: o["extraction"]["status"] != "pending"
    )
    assert opp["pack"] == pack and opp["extraction"]["status"] == "ready", opp
    assert opp["title"] == read["title"]
    assert all(opp["attributes"][k] == v for k, v in read.items())

    # An application in the pack's pipeline, with the default profile of that pack.
    app = await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})
    assert app.status_code == 201, app.text
    app = app.json()
    assert app["stage"]["code"] == first_stage and app["profile_id"] == profile.json()["id"]

    # Both documents, written in the background from this pack's prompts, then checked for claims.
    first = await write(client, app["id"], first_doc)
    second = await write(client, app["id"], second_doc)
    for doc in (first, second):
        assert doc["status"] == "ready" and doc["claims_status"] == "checked", doc
    prompt = next(p for p in model_server.prompts if p.startswith("You write") and profile_in["summary"] in p)
    assert "{{" not in prompt and read["title"] in prompt
    flagged = {(w["kind"], w["quote"]) for d in (first, second) for w in d["claim_warnings"]}
    if UNSUPPORTED[pack]:
        assert ("unsupported", UNSUPPORTED[pack]) in flagged
    if pack == "tender":
        assert ("confirm", "[CONFIRM: insurance cover]") in flagged

    pdf = await poll_pdf(client, f"/api/v1/applications/{app['id']}/documents/{first['id']}/pdf")
    assert pdf.content.startswith(b"%PDF-")

    # The kit carries the documents and the pack's own questions; a submission moves it to "submitted".
    kit = (await client.get(f"/api/v1/applications/{app['id']}/kit")).json()
    assert {d["document"]["document_type"] for d in kit["documents"]} == {first_doc, second_doc}
    asked = {a["key"] for a in kit["answers"]}
    job_only = {"needs_sponsorship", "notice_period", "gender"}
    assert asked and not asked & job_only
    sent = await client.post(f"/api/v1/applications/{app['id']}/submissions", json={"note": "On the portal"})
    assert sent.status_code == 201, sent.text
    moved = (await client.get(f"/api/v1/applications/{app['id']}")).json()
    assert moved["stage"]["code"] == submitted_stage

    for code in later:
        step = await client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": code})
        assert step.status_code == 200, step.text
    done = (await client.get(f"/api/v1/applications/{app['id']}")).json()
    assert done["stage"]["code"] == later[-1] and done["stage"]["category"] == "success"
    wrong = await client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": "offer"})
    assert wrong.status_code in (404, 422)

    # Lists keep to their pack.
    listed = (await client.get("/api/v1/applications", params={"pack": pack})).json()["items"]
    assert [a["id"] for a in listed] == [app["id"]]
    assert (await client.get("/api/v1/applications", params={"pack": "job"})).json()["items"] == []
    profiles = (await client.get("/api/v1/profiles", params={"pack": pack})).json()["items"]
    assert [p["id"] for p in profiles] == [profile.json()["id"]]


async def test_each_pack_describes_itself_for_the_screens(client, owner):
    for pack, options in (
        ("job", {"locations", "remote_only", "needs_sponsorship"}),
        ("tender", {"locations"}),
        ("grant", {"locations"}),
        ("contract", {"locations", "remote_only"}),
    ):
        body = (await client.get(f"/api/v1/packs/{pack}")).json()
        assert set(body["search_options"]) == options, pack
        assert body["auto"] is (pack == "job")
        props = body["profile_schema"]["properties"]
        assert all("x-label" in p for p in props.values()), pack
        assert all({"en", "ne"} <= set(p["x-label"]) for p in props.values()), pack


async def test_tenders_from_contracts_finder_fill_the_inbox_without_duplicates(
    client, owner, site, model_server, worker
):
    serve(site, CONTRACTS_FINDER)
    model(model_server, {}, scores={"Case management software for children's services": 86, "Grounds maintenance": 20})
    await client.post("/api/v1/profiles", json=TENDER_PROFILE)
    kinds = (await client.get("/api/v1/source-kinds", params={"pack": "tender"})).json()["items"]
    assert [k["kind"] for k in kinds] == ["contracts_finder"]
    made = await client.post("/api/v1/sources", json={"pack": "tender", "kind": "contracts_finder", "config": {}})
    assert made.status_code == 201, made.text
    search = await client.post("/api/v1/searches", json={"pack": "tender", "name": "Councils", "criteria": {}})
    assert search.status_code == 201, search.text

    inbox = await poll(
        client,
        "/api/v1/matches?pack=tender",
        lambda b: len(b["items"]) >= 2 and all(m["score_status"] != "pending" for m in b["items"]),
        within=60,
    )
    titles = [(m["opportunity"]["title"], m["score"]) for m in inbox["items"]]
    assert titles == [("Case management software for children's services", 86), ("Grounds maintenance", 20)]
    best = inbox["items"][0]["opportunity"]
    assert best["pack"] == "tender" and best["issuer_name"] == "Example City Council"
    assert best["source_url"].endswith("/notice/6b1f8a3e-1111-4c22-9a33-2b8f00000001")
    assert (await client.get("/api/v1/matches?pack=job")).json()["items"] == []

    from sqlalchemy import update

    from apply.logic import scheduler
    from apply.store.sql.models import Source

    rt = client._transport.app.state.runtime
    async with rt.db.engine.begin() as conn:
        await conn.execute(update(Source).values(last_fetched_at=None))
    await scheduler.tick(rt)
    await poll(client, "/api/v1/sources?pack=tender", lambda b: all(s["last_status"] == "ok" for s in b["items"]))
    again = (await client.get("/api/v1/matches?pack=tender")).json()
    assert len(again["items"]) == 2


async def test_grants_from_grants_gov_fill_the_inbox(client, owner, site, model_server, worker):
    serve(site, GRANTS_GOV)
    model(model_server, {}, scores={"Rural Health Network Development Program": 91, "STEM Education Research": 30})
    await client.post("/api/v1/profiles", json=GRANT_PROFILE)
    made = await client.post(
        "/api/v1/sources", json={"pack": "grant", "kind": "grants_gov", "config": {"keyword": "rural health"}}
    )
    assert made.status_code == 201, made.text
    await client.post("/api/v1/searches", json={"pack": "grant", "name": "Health", "criteria": {}})
    inbox = await poll(
        client,
        "/api/v1/matches?pack=grant",
        lambda b: len(b["items"]) >= 2 and all(m["score_status"] != "pending" for m in b["items"]),
        within=60,
    )
    best = inbox["items"][0]
    assert best["score"] == 91 and best["opportunity"]["issuer_name"] == "Example Health Agency"
    opp = (await client.get(f"/api/v1/opportunities/{best['opportunity']['id']}")).json()
    assert opp["attributes"]["award_ceiling"] == "$300,000" and opp["attributes"]["number"] == "EXH-27-011"
    assert opp["source_url"] == "https://www.grants.gov/search-results-detail/358001"
    posted = [(path, h) for path, h in site.hits if path.startswith("/v1/api/")]
    assert posted and all("apply" in h.get("user-agent", "").lower() for _, h in posted)


async def test_a_bad_source_config_or_the_wrong_pack_is_refused(client, owner):
    bad = await client.post(
        "/api/v1/sources", json={"pack": "grant", "kind": "grants_gov", "config": {"keyword": "<script>"}}
    )
    assert bad.status_code == 422
    wrong_pack = await client.post("/api/v1/sources", json={"pack": "contract", "kind": "grants_gov", "config": {}})
    assert wrong_pack.status_code in (404, 422)
