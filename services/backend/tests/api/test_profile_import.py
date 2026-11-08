"""
A profile from an uploaded resume, over HTTP with the real worker and the fake model: saved at once, read in the
background, the person's edits winning; read again; the file kept in the bucket; and duplicating a profile.
"""

import json

import pytest

from tests.conftest import poll
from tests.support.documents import docx, resume_pdf, scan_pdf

from .helpers import PROFILE

READ = {
    "summary": "Backend engineer who ships reliable APIs.",
    "profile": {
        "full_name": "Sam Rai",
        "email": "sam@example.com",
        "phone": "",
        "location": "Kathmandu",
        "links": [],
        "skills": ["Python", "Django", "PostgreSQL", "Celery"],
        "experience": [
            {
                "title": "Backend Engineer",
                "organisation": "Himal Tech",
                "start": "2019",
                "end": "2025",
                "location": "",
                "highlights": ["Built Django REST APIs on PostgreSQL", "Moved slow work to Celery"],
            }
        ],
        "education": [
            {
                "qualification": "BE Computer Engineering",
                "institution": "Example University",
                "year": "2018",
                "notes": "",
            }
        ],
        "certifications": [],
        "languages": [],
        "work_authorization": "",
    },
}


def reads(model_server, reply: dict = READ) -> None:
    def respond(body):
        if "format" in body and "profile" in body["format"].get("properties", {}):
            return json.dumps(reply)
        return "{}"

    model_server.responder = respond


async def upload(client, data: bytes, filename: str = "Sam Rai CV.pdf", **form) -> object:
    return await client.post(
        "/api/v1/profiles/import", files={"file": (filename, data, "application/octet-stream")}, data=form
    )


async def test_a_resume_becomes_a_profile_read_by_the_model(client, owner, model_server, worker, rt):
    reads(model_server)
    pdf = resume_pdf()
    made = await upload(client, pdf)
    assert made.status_code == 202, made.text
    profile = made.json()
    assert profile["reading"] == {"status": "pending", "error_code": None, "edited": False}
    assert profile["source"] == {"name": "Sam Rai CV.pdf", "kind": "pdf", "size": len(pdf)}
    assert profile["name"] == "Sam Rai CV" and profile["is_default"]  # the first in its pack

    done = await poll(client, f"/api/v1/profiles/{profile['id']}", lambda p: p["reading"]["status"] != "pending")
    assert done["reading"] == {"status": "ready", "error_code": None, "edited": False}
    assert done["name"] == "Sam Rai"  # the person's name, once read
    assert done["summary"] == READ["summary"]
    assert done["attributes"]["experience"][0]["highlights"] == READ["profile"]["experience"][0]["highlights"]
    checked = await client.patch(f"/api/v1/profiles/{profile['id']}", json={"summary": "Checked by me."})
    assert checked.json()["reading"] == {"status": "ready", "error_code": None, "edited": True}

    # The model read the document's own text, fenced as data, and answered to the pack's fields.
    asked = next(r for r in model_server.requests if "format" in r)
    assert "Built Django REST APIs on PostgreSQL" in asked["messages"][0]["content"]
    assert "<<<DOCUMENT" in asked["messages"][0]["content"]
    assert "experience" in asked["format"]["properties"]["profile"]["properties"]

    # The file is in the bucket, under the account, and comes back as it went in.
    me = (await client.get("/api/v1/auth/me")).json()["id"]
    stored = [f.key for f in await rt.files.files(f"owners/{me}/profiles/")]
    assert stored == [f"owners/{me}/profiles/{profile['id']}/source.pdf"]
    source = await client.get(f"/api/v1/profiles/{profile['id']}/source")
    assert source.status_code == 200 and source.content == pdf
    assert source.headers["content-type"] == "application/pdf"
    assert source.headers["content-disposition"] == "attachment; filename*=UTF-8''Sam%20Rai%20CV.pdf"


async def test_a_word_document_and_a_name_given_up_front(client, owner, model_server, worker):
    reads(model_server, {"summary": "", "profile": {"full_name": "", "skills": ["Go"]}})
    made = await upload(
        client,
        docx([("Backend engineer with Go", False), ("Built APIs in Go at Himal Tech", True)]),
        "cv.docx",
        name="Go roles",
    )
    assert made.status_code == 202, made.text
    done = await poll(client, f"/api/v1/profiles/{made.json()['id']}", lambda p: p["reading"]["status"] != "pending")
    assert done["name"] == "Go roles" and done["attributes"]["skills"] == ["Go"]
    assert done["source"]["kind"] == "docx"


async def test_edits_made_while_it_is_being_read_win(client, owner, model_server, rt):
    from apply.logic.background import QUEUES
    from apply.worker import build

    reads(model_server)
    profile = (await upload(client, resume_pdf())).json()
    edited = await client.patch(f"/api/v1/profiles/{profile['id']}", json={"summary": "I wrote this myself."})
    assert edited.json()["reading"]["status"] == "stopped"
    await build(rt, queues=list(QUEUES), concurrency=1, schedule=False).run_until_idle()
    after = (await client.get(f"/api/v1/profiles/{profile['id']}")).json()
    assert after["summary"] == "I wrote this myself." and after["attributes"]["experience"] == []


async def test_when_the_model_fails_it_says_so_and_can_read_again(client, owner, model_server, worker):
    model_server.status = 500
    profile = (await upload(client, resume_pdf())).json()
    failed = await poll(client, f"/api/v1/profiles/{profile['id']}", lambda p: p["reading"]["status"] != "pending")
    assert failed["reading"]["status"] == "failed" and failed["reading"]["error_code"]
    assert failed["attributes"]["experience"] == []  # nothing guessed

    model_server.status = 200
    reads(model_server)
    again = await client.post(f"/api/v1/profiles/{profile['id']}/read")
    assert again.status_code == 202 and again.json()["reading"]["status"] == "pending"
    done = await poll(client, f"/api/v1/profiles/{profile['id']}", lambda p: p["reading"]["status"] != "pending")
    assert done["reading"]["status"] == "ready" and done["attributes"]["skills"]


async def test_a_reading_with_nothing_in_it_is_a_failure_not_an_empty_profile(client, owner, model_server, worker):
    reads(model_server, {"summary": "", "profile": {}})
    profile = (await upload(client, resume_pdf())).json()
    done = await poll(client, f"/api/v1/profiles/{profile['id']}", lambda p: p["reading"]["status"] != "pending")
    assert done["reading"] == {"status": "failed", "error_code": "EXTRACT_FAILED", "edited": False}


async def test_any_pack_reads_its_own_document(client, owner, model_server, worker):
    reads(
        model_server,
        {"summary": "We build bridges.", "profile": {"legal_name": "Himal Works Pvt Ltd", "sectors": ["Roads"]}},
    )
    made = await upload(
        client, resume_pdf("# Himal Works Pvt Ltd\n\nWe build roads and bridges across Nepal."), pack="tender"
    )
    assert made.status_code == 202, made.text
    assert made.json()["kind"] == "organisation"
    done = await poll(client, f"/api/v1/profiles/{made.json()['id']}", lambda p: p["reading"]["status"] != "pending")
    assert done["attributes"]["legal_name"] == "Himal Works Pvt Ltd" and done["attributes"]["sectors"] == ["Roads"]
    asked = next(r for r in model_server.requests if "format" in r)
    assert "capability statement" in asked["messages"][0]["content"]


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (scan_pdf(), "UPLOAD_NO_TEXT"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "UPLOAD_UNSUPPORTED"),
        (b"x" * 5_000_001, "UPLOAD_TOO_LARGE"),
    ],
    ids=["a scan", "an image", "too large"],
)
async def test_what_cant_be_read_is_refused_and_nothing_is_made(client, owner, rt, data, code):
    refused = await upload(client, data)
    assert refused.status_code == 422 and refused.json()["code"] == code
    assert (await client.get("/api/v1/profiles")).json()["items"] == []
    assert await rt.files.files("owners/") == []


async def test_an_unknown_pack_is_refused(client, owner):
    refused = await upload(client, resume_pdf(), pack="nope")
    assert refused.status_code == 404 and refused.json()["code"] == "PACK_NOT_FOUND"


async def test_deleting_the_profile_removes_its_file(client, owner, model_server, rt):
    profile = (await upload(client, resume_pdf())).json()
    assert len(await rt.files.files("owners/")) == 1
    assert (await client.delete(f"/api/v1/profiles/{profile['id']}")).status_code == 204
    assert await rt.files.files("owners/") == []


async def test_a_typed_in_profile_has_nothing_to_read(client, owner):
    profile = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    assert profile["source"] is None and profile["reading"] is None
    for call in (
        client.post(f"/api/v1/profiles/{profile['id']}/read"),
        client.get(f"/api/v1/profiles/{profile['id']}/source"),
    ):
        refused = await call
        assert refused.status_code == 409 and refused.json()["code"] == "PROFILE_NOT_READ"


async def test_only_the_owner_sees_or_reads_it(client, owner, other_client):
    profile = (await upload(client, resume_pdf())).json()
    for call in (
        other_client.get(f"/api/v1/profiles/{profile['id']}/source"),
        other_client.post(f"/api/v1/profiles/{profile['id']}/read"),
        other_client.post(f"/api/v1/profiles/{profile['id']}/duplicate"),
    ):
        assert (await call).status_code == 404


async def test_signed_out_nothing_is_uploaded(client, rt):
    from tests.conftest import TEST_API

    refused = await client.post(
        "/api/v1/profiles/import", files={"file": ("cv.pdf", resume_pdf())}, headers={"Origin": TEST_API}
    )
    assert refused.status_code == 401
    assert await rt.files.files("") == []


# ── duplicating ──────────────────────────────────────────────────────────────


async def test_duplicating_a_profile_to_change_what_is_different(client, owner):
    original = (await client.post("/api/v1/profiles", json=PROFILE | {"tone_instructions": "Plain."})).json()
    copy = await client.post(f"/api/v1/profiles/{original['id']}/duplicate")
    assert copy.status_code == 201, copy.text
    copy = copy.json()
    assert copy["id"] != original["id"] and copy["name"] == "Backend (copy)"
    assert not copy["is_default"] and original["is_default"]
    for same in ("pack", "kind", "summary", "attributes", "tone_instructions"):
        assert copy[same] == original[same]

    changed = await client.patch(f"/api/v1/profiles/{copy['id']}", json={"summary": "Data engineer."})
    assert changed.json()["summary"] == "Data engineer."
    assert (await client.get(f"/api/v1/profiles/{original['id']}")).json()["summary"] == PROFILE["summary"]

    named = await client.post(f"/api/v1/profiles/{original['id']}/duplicate", json={"name": "Copia de Backend"})
    assert named.json()["name"] == "Copia de Backend"


async def test_a_copy_of_an_uploaded_profile_is_not_tied_to_its_file(client, owner, model_server, worker):
    reads(model_server)
    profile = (await upload(client, resume_pdf())).json()
    await poll(client, f"/api/v1/profiles/{profile['id']}", lambda p: p["reading"]["status"] != "pending")
    copy = (await client.post(f"/api/v1/profiles/{profile['id']}/duplicate")).json()
    assert copy["source"] is None and copy["reading"] is None and copy["attributes"]["skills"]
