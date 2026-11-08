"""Pasting a posting: JSON-LD at once, the model in the background, the person when neither works."""

from tests.conftest import poll

from .helpers import EXTRACTED, POSTING, ld_page

JOB_LD = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Data Analyst",
    "hiringOrganization": {"@type": "Organization", "name": "Example Retail"},
    "description": "<p>SQL and dashboards.</p>",
    "jobLocation": {"@type": "Place", "address": {"addressLocality": "Kathmandu", "addressCountry": "NP"}},
}


async def test_a_link_with_json_ld_is_read_at_once(client, owner, site, model_server):
    site.add("/jobs/42", ld_page(JOB_LD))
    response = await client.post("/api/v1/opportunities", json={"url": f"{site.url}/jobs/42?utm_source=x"})
    assert response.status_code == 201, response.text
    opp = response.json()
    assert opp["extraction"] == {"status": "ready", "method": "json_ld", "error_code": None, "edited": False}
    assert opp["title"] == "Data Analyst" and opp["issuer_name"] == "Example Retail"
    assert opp["attributes"]["location"] == "Kathmandu, NP"
    assert opp["source_url"] == f"{site.url}/jobs/42"  # canonical: no tracking parameters
    assert model_server.requests == []  # no model needed

    again = await client.post("/api/v1/opportunities", json={"url": f"{site.url}/jobs/42#apply"})
    assert again.status_code == 200 and again.json()["id"] == opp["id"]
    assert len(site.hits) == 1  # not fetched twice


async def test_pasted_text_is_read_by_the_model_in_the_background(client, owner, model_server, worker):
    model_server.responder = lambda body: __import__("json").dumps(EXTRACTED)
    response = await client.post("/api/v1/opportunities", json={"text": POSTING})
    assert response.status_code == 201
    opp = response.json()
    assert opp["extraction"]["status"] == "pending"
    assert opp["title"].startswith("Senior Backend Engineer at Acme")  # the first line, while it waits

    done = await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    assert done["extraction"] == {"status": "ready", "method": "model", "error_code": None, "edited": False}
    assert done["title"] == "Senior Backend Engineer" and done["issuer_name"] == "Acme Robotics"
    assert done["attributes"]["workplace"] == "remote"
    request = model_server.requests[-1]
    assert request["think"] is False and request["format"]["required"]
    assert "<<<POSTING" in request["messages"][0]["content"] and "Celery" in request["messages"][0]["content"]

    again = await client.post("/api/v1/opportunities", json={"text": "  " + POSTING + "\n"})
    assert again.status_code == 200 and again.json()["id"] == opp["id"]


async def test_a_page_without_json_ld_goes_to_the_model(client, owner, site, model_server, worker):
    model_server.responder = lambda body: __import__("json").dumps(EXTRACTED)
    site.add(
        "/careers/7",
        "<html><body><main><h1>Senior Backend Engineer</h1>" + "<p>" + POSTING * 3 + "</p></main></body></html>",
    )
    opp = (await client.post("/api/v1/opportunities", json={"url": f"{site.url}/careers/7"})).json()
    assert opp["extraction"]["status"] == "pending" and opp["title"] == "Senior Backend Engineer"
    done = await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    assert done["extraction"]["method"] == "model" and done["issuer_name"] == "Acme Robotics"


async def test_a_blocked_page_is_left_to_the_person(client, owner, site, model_server):
    site.add("/blocked", "no", status=403)
    opp = (await client.post("/api/v1/opportunities", json={"url": f"{site.url}/blocked"})).json()
    assert opp["extraction"] == {"status": "manual", "method": "manual", "error_code": "FETCH_BLOCKED", "edited": False}
    assert opp["title"] == "" and opp["issuer_name"] == ""  # no guesses
    site.add("/wall", "<html><body><p>Please verify you are human. Complete the CAPTCHA.</p></body></html>")
    wall = (await client.post("/api/v1/opportunities", json={"url": f"{site.url}/wall"})).json()
    assert wall["extraction"]["status"] == "manual" and wall["extraction"]["error_code"] == "FETCH_BLOCKED"
    assert model_server.requests == []


async def test_links_that_must_not_be_fetched_are_refused(client, owner):
    for url, code in (("ftp://example.com/job", "URL_NOT_ALLOWED"), ("file:///etc/passwd", "URL_NOT_ALLOWED")):
        response = await client.post("/api/v1/opportunities", json={"url": url})
        assert response.status_code == 422 and response.json()["code"] == code
    both = await client.post("/api/v1/opportunities", json={"url": "https://example.com", "text": "x"})
    assert both.status_code == 422 and both.json()["code"] == "URL_OR_TEXT_REQUIRED"
    neither = await client.post("/api/v1/opportunities", json={})
    assert neither.json()["code"] == "URL_OR_TEXT_REQUIRED"


async def test_a_failing_model_leaves_the_fields_to_the_person(client, owner, model_server, worker):
    model_server.status = 500
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    done = await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    assert done["extraction"]["status"] == "manual" and done["extraction"]["error_code"] == "LLM_UNREACHABLE"

    model_server.status = 200
    model_server.responder = lambda body: __import__("json").dumps(EXTRACTED)
    retried = await client.post(f"/api/v1/opportunities/{opp['id']}/extract")
    assert retried.status_code == 202 and retried.json()["extraction"]["status"] == "pending"
    done = await poll(client, f"/api/v1/opportunities/{opp['id']}", lambda o: o["extraction"]["status"] != "pending")
    assert done["extraction"]["status"] == "ready"


async def test_the_person_corrects_the_fields_and_the_model_does_not_overwrite_them(client, owner, model_server, rt):
    model_server.responder = lambda body: __import__("json").dumps(EXTRACTED)
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    fixed = await client.patch(
        f"/api/v1/opportunities/{opp['id']}",
        json={"attributes": {"job_title": "Staff Engineer", "company_name": "Acme"}},
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["title"] == "Staff Engineer" and fixed.json()["issuer_name"] == "Acme"
    assert fixed.json()["extraction"]["status"] == "manual"
    from apply.worker import build

    await build(rt, queues=["llm"], concurrency=1).run_until_idle()  # the queued read runs now: changes nothing
    after = (await client.get(f"/api/v1/opportunities/{opp['id']}")).json()
    assert after["title"] == "Staff Engineer"
    bad = await client.patch(f"/api/v1/opportunities/{opp['id']}", json={"attributes": {"salary": 1}})
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_ATTRIBUTES"
