"""
Review, over HTTP with the real worker: a written document is checked for claims the profile
doesn't back, reviewed (edited, warnings decided), turned into a PDF, and sent by hand with the kit.
"""

import io
import json

from pypdf import PdfReader

from tests.conftest import poll

from .helpers import POSTING, PROFILE

EMBELLISHED = """# Sam Rai
sam@example.com

### Experience
- Backend Engineer, Himal Tech: built Django REST APIs on PostgreSQL
- Led a team of 12 engineers building fleet software
- Mentored [CONFIRM: how many] juniors
"""


def model(model_server, resume: str = EMBELLISHED):
    def respond(body):
        prompt = body["messages"][0]["content"]
        if "format" in body and "claims" in body["format"].get("properties", {}):
            return json.dumps(
                {
                    "claims": [
                        {"quote": "building fleet software", "reason": "Your profile doesn't mention fleet software."},
                        {
                            "quote": "worked at Brightwater Logistics",
                            "reason": "Not in the document at all: must be dropped.",
                        },
                    ]
                }
            )
        if "format" in body:
            return json.dumps(
                {k: "" for k in body["format"]["properties"]}
                | {"job_title": "Senior Backend Engineer", "company_name": "Acme Robotics"}
            )
        return resume if "You write resumes" in prompt else "Dear Hiring Manager,\n\nSam Rai"

    model_server.responder = respond


async def written(client, worker) -> tuple[str, dict]:
    await client.post("/api/v1/profiles", json=PROFILE)
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    base = f"/api/v1/applications/{app['id']}/documents"
    doc = (await client.post(base, json={"document_type": "resume"})).json()
    doc = await poll(
        client, f"{base}/{doc['id']}", lambda d: d["status"] == "ready" and d["claims_status"] != "pending"
    )
    return app["id"], doc


async def test_claims_are_checked_reviewed_and_the_pdf_is_made(client, owner, model_server, worker):
    model(model_server)
    app_id, doc = await written(client, worker)
    base = f"/api/v1/applications/{app_id}/documents"
    assert doc["claims_status"] == "checked"
    warnings = {(w["kind"], w["quote"]) for w in doc["claim_warnings"]}
    assert ("confirm", "[CONFIRM: how many]") in warnings
    assert ("unsupported", "building fleet software") in warnings
    assert any(k == "number" and "12" in q for k, q in warnings)
    assert not any("Brightwater" in q for _, q in warnings)  # not in the document: dropped
    assert not any(k == "number" and "2019" in q for k, q in warnings)

    # The page in the template, and the PDF: that page printed, tagged, with the person's name as its title.
    page = await poll_pdf(client, f"{base}/{doc['id']}/html")
    assert page.headers["content-type"].startswith("text/html")
    assert "sandbox" in page.headers["content-security-policy"] and page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["content-disposition"].startswith("inline")
    assert "<title>Sam Rai - Resume</title>" in page.text and "<h1>Sam Rai</h1>" in page.text
    download = await client.get(f"{base}/{doc['id']}/html", params={"download": True})
    assert download.headers["content-disposition"].startswith("attachment") and download.content == page.content
    pdf = await poll_pdf(client, f"{base}/{doc['id']}/pdf")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(pdf.content))
    assert "/StructTreeRoot" in reader.trailer["/Root"] and reader.metadata["/Title"] == "Sam Rai - Resume"
    # And as a Word file to edit: a download, with the same outline.
    word = await poll_pdf(client, f"{base}/{doc['id']}/docx")
    assert word.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert word.headers["content-disposition"].startswith("attachment") and word.content.startswith(b"PK")
    from docx import Document as read_docx

    paragraphs = read_docx(io.BytesIO(word.content)).paragraphs
    assert (paragraphs[0].style.name, paragraphs[0].text) == ("Heading 1", "Sam Rai")
    assert ("List Bullet", "Led a team of 12 engineers building fleet software") in [
        (x.style.name, x.text) for x in paragraphs
    ]

    # "It's true" on the number; edit the rest away: a new version, checked again, the decision kept.
    number = next(w for w in doc["claim_warnings"] if w["kind"] == "number")
    kept = await client.post(f"{base}/{doc['id']}/warnings/{number['id']}", json={"resolution": "kept"})
    assert next(w for w in kept.json()["claim_warnings"] if w["id"] == number["id"])["resolved"] == "kept"
    fixed = EMBELLISHED.replace(" building fleet software", "").replace("- Mentored [CONFIRM: how many] juniors\n", "")
    edited = await client.put(f"{base}/{doc['id']}/content", json={"content_markdown": fixed})
    assert edited.status_code == 201
    assert edited.json()["version"] == 2 and edited.json()["source"] == "edited" and edited.json()["is_active"]
    again = await poll(client, f"{base}/{edited.json()['id']}", lambda d: d["claims_status"] != "pending")
    assert {w["kind"] for w in again["claim_warnings"] if not w["resolved"]} <= {"unsupported"}
    assert next(w for w in again["claim_warnings"] if w["kind"] == "number")["resolved"] == "kept"
    old = (await client.get(f"{base}/{doc['id']}")).json()
    assert not old["is_active"] and old["content_markdown"].endswith(EMBELLISHED.split("\n\n", 1)[1].strip() + "\n")

    reviewed = await client.post(f"{base}/{again['id']}/review", json={"reviewed": True})
    assert reviewed.json()["reviewed_at"] is not None
    pdf2 = await poll_pdf(client, f"{base}/{again['id']}/pdf")
    assert pdf2.content != pdf.content


async def poll_pdf(client, path):
    import asyncio

    for _ in range(200):
        response = await client.get(path)
        if response.status_code == 200:
            return response
        assert response.status_code == 409 and response.json()["code"] == "RENDER_PENDING", response.text
        await asyncio.sleep(0.05)
    raise AssertionError("the PDF never came")


async def test_the_kit_and_a_submission(client, owner, model_server, worker):
    model(model_server)
    app_id, doc = await written(client, worker)
    kit = (await client.get(f"/api/v1/applications/{app_id}/kit")).json()
    assert [d["document"]["id"] for d in kit["documents"]] == [doc["id"]]
    assert kit["documents"][0]["open_warnings"] >= 2
    keys = {a["key"]: a for a in kit["answers"]}
    assert keys["gender"]["is_sensitive"] and keys["gender"]["answer"] == "decline"  # seeded, declined
    assert keys["needs_sponsorship"]["answer_type"] == "yes_no"
    assert keys["gender"]["question"]["ne"]

    await client.patch(f"/api/v1/answers/{keys['notice_period']['id']}", json={"answer": "One month"})
    await client.patch(f"/api/v1/answers/{keys['gender']['id']}", json={"answer": "woman"})
    bad = await client.patch(f"/api/v1/answers/{keys['needs_sponsorship']['id']}", json={"answer": "maybe"})
    assert bad.status_code == 422

    submitted = await client.post(f"/api/v1/applications/{app_id}/submissions", json={"note": "Via their site"})
    assert submitted.status_code == 201
    record = submitted.json()
    assert record["channel"] == "manual" and record["documents"][0]["version"] == 1
    gender = next(a for a in record["answers"] if a["key"] == "gender")
    assert gender == {"key": "gender", "question": "Gender (equal-opportunity question)", "state": "provided"}
    assert next(a for a in record["answers"] if a["key"] == "notice_period")["value"] == "One month"

    app = (await client.get(f"/api/v1/applications/{app_id}")).json()
    assert app["submitted_at"] is not None and app["stage"]["code"] == "in_progress"
    undone = await client.post(f"/api/v1/submissions/{record['id']}/undo")
    assert undone.json()["undone_at"] is not None
    app = (await client.get(f"/api/v1/applications/{app_id}")).json()
    assert app["submitted_at"] is None and app["stage"]["code"] == "new"


async def test_sensitive_answers_never_reach_the_model(client, owner, model_server, worker):
    model(model_server)
    await client.post("/api/v1/answers/defaults")
    answers = (await client.get("/api/v1/answers")).json()["items"]
    gender = next(a for a in answers if a["key"] == "gender")
    await client.patch(f"/api/v1/answers/{gender['id']}", json={"answer": "non_binary"})
    await written(client, worker)
    assert not any("non_binary" in json.dumps(r) for r in model_server.requests)


async def test_answers_of_your_own(client, owner):
    made = await client.post(
        "/api/v1/answers",
        json={
            "key": "code_profile",
            "question": {"en": "Code hosting profile"},
            "answer": "https://sam.example.com",
            "answer_type": "url",
        },
    )
    assert made.status_code == 201 and made.json()["question"]["ne"] == "Code hosting profile"
    again = await client.post("/api/v1/answers", json={"key": "code_profile", "question": {"en": "x"}})
    assert again.status_code == 409 and again.json()["code"] == "ANSWER_EXISTS"
    assert (await client.post("/api/v1/answers/defaults")).json()["added"] == 13
    assert (await client.post("/api/v1/answers/defaults")).json()["added"] == 0
    assert (await client.delete(f"/api/v1/answers/{made.json()['id']}")).status_code == 204


async def test_another_account_cant_touch_it(client, owner, other_client, model_server, worker):
    model(model_server)
    app_id, doc = await written(client, worker)
    base = f"/api/v1/applications/{app_id}/documents/{doc['id']}"
    for call in (
        other_client.get(f"{base}/pdf"),
        other_client.put(f"{base}/content", json={"content_markdown": "x"}),
        other_client.post(f"{base}/review", json={}),
        other_client.get(f"/api/v1/applications/{app_id}/kit"),
        other_client.post(f"/api/v1/applications/{app_id}/submissions", json={}),
    ):
        assert (await call).status_code == 404


async def test_its_wrong_with_whats_true_then_rewritten_from_the_corrections(client, owner, model_server, worker, rt):
    from apply.logic import portable

    prompts: list[str] = []
    rewritten = EMBELLISHED.replace("12 engineers building fleet software", "5 engineers").replace(
        "- Mentored [CONFIRM: how many] juniors\n", "- Moved to Kathmandu\n"
    )
    model(model_server)
    plain = model_server.responder

    def respond(body):
        prompt = body["messages"][0]["content"]
        prompts.append(prompt)
        return rewritten if "THIS IS A REWRITE" in prompt else plain(body)

    model_server.responder = respond
    app_id, doc = await written(client, worker)
    base = f"/api/v1/applications/{app_id}/documents"
    number = next(w for w in doc["claim_warnings"] if w["kind"] == "number")
    fleet = next(w for w in doc["claim_warnings"] if w["quote"] == "building fleet software")
    # Each warning in its sentence.
    assert number["quote"] == "12 engineers"
    assert number["sentence"] == fleet["sentence"] == "Led a team of 12 engineers building fleet software"

    # Nothing said yet: nothing to rewrite from.
    nothing = await client.post(f"{base}/{doc['id']}/rewrite", json={"notes": "  "})
    assert nothing.status_code == 409 and nothing.json()["code"] == "NOTHING_TO_REWRITE"

    # "It's wrong": with what's true, or empty to take it out. Too long a correction is refused.
    too_long = await client.post(
        f"{base}/{doc['id']}/warnings/{number['id']}", json={"resolution": "wrong", "correction": "x" * 501}
    )
    assert too_long.status_code == 422
    wrong = await client.post(
        f"{base}/{doc['id']}/warnings/{number['id']}", json={"resolution": "wrong", "correction": " 5 engineers "}
    )
    marked = next(w for w in wrong.json()["claim_warnings"] if w["id"] == number["id"])
    assert marked["resolved"] == "wrong" and marked["correction"] == "5 engineers"
    await client.post(f"{base}/{doc['id']}/warnings/{fleet['id']}", json={"resolution": "wrong"})
    # Looked at again, then wrong once more: the correction goes with "open".
    reopened = await client.post(f"{base}/{doc['id']}/warnings/{number['id']}", json={"resolution": "open"})
    assert next(w for w in reopened.json()["claim_warnings"] if w["id"] == number["id"])["correction"] is None
    await client.post(
        f"{base}/{doc['id']}/warnings/{number['id']}", json={"resolution": "wrong", "correction": "5 engineers"}
    )

    queued = await client.post(f"{base}/{doc['id']}/rewrite", json={"notes": "Say I moved to Kathmandu."})
    assert queued.status_code == 202 and queued.json()["status"] == "pending"
    assert queued.json()["source"] == "rewritten"
    again = await poll(
        client, f"{base}/{queued.json()['id']}", lambda d: d["status"] == "ready" and d["claims_status"] != "pending"
    )
    assert again["version"] == 2 and again["is_active"] and again["source"] == "rewritten"
    assert "5 engineers" in again["content_markdown"] and "fleet" not in again["content_markdown"]
    assert not (await client.get(f"{base}/{doc['id']}")).json()["is_active"]

    # The writer had the version read, what's wrong in it, what's true, and the notes, as the person's facts.
    brief = next(p for p in prompts if "THIS IS A REWRITE" in p)
    assert "<<<PREVIOUS\n" in brief and "Led a team of 12 engineers building fleet software" in brief
    assert (
        '"12 engineers" (in "Led a team of 12 engineers building fleet software") is wrong. What is true: 5 engineers'
        in brief
    )
    assert (
        '"building fleet software" (in "Led a team of 12 engineers building fleet software") is wrong. Take it out.'
        in brief
    )
    assert "- Say I moved to Kathmandu." in brief and '"corrections_from_you"' in brief and '"notes_from_you"' in brief
    # Checked against them too: the corrected number isn't flagged.
    assert not [w for w in again["claim_warnings"] if w["kind"] == "number"]

    # Edited after, and exported: the corrections stay with the document.
    edited = await client.put(f"{base}/{again['id']}/content", json={"content_markdown": rewritten + "\nMore.\n"})
    assert edited.status_code == 201 and edited.json()["source"] == "edited"
    me = (await client.get("/api/v1/auth/me")).json()
    async with rt.db.transaction() as session:
        exported = await portable.export(session, me["id"])
    docs = [d for a in exported.applications for d in a.documents]
    assert {d.source for d in docs} == {"generated", "rewritten", "edited"}
    last = next(d for d in docs if d.source == "edited")
    assert [c["correction"] for c in last.revision["corrections"]] == ["5 engineers", ""]
