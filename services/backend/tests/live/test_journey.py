"""
The first journey with the real model and the real worker: paste a posting, the model reads it, create an
application, write a resume, poll until it is ready. Timings are printed.
"""

import time

from tests.api.helpers import POSTING, PROFILE
from tests.conftest import poll


async def test_a_tailored_resume_is_written_by_the_local_model_end_to_end(client, owner, worker):
    started = time.monotonic()
    profile = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    read = await poll(
        client,
        f"/api/v1/opportunities/{opp['id']}",
        lambda o: o["extraction"]["status"] != "pending",
        within=300,
        every=0.5,
    )
    read_seconds = time.monotonic() - started
    assert read["extraction"]["status"] == "ready", read
    assert "backend" in read["title"].lower() and "acme" in read["issuer_name"].lower()

    app = (
        await client.post("/api/v1/applications", json={"opportunity_id": opp["id"], "profile_id": profile["id"]})
    ).json()
    started = time.monotonic()
    queued = await client.post(f"/api/v1/applications/{app['id']}/documents", json={"document_type": "resume"})
    assert queued.status_code == 202
    doc = await poll(
        client,
        f"/api/v1/applications/{app['id']}/documents/{queued.json()['id']}",
        lambda d: d["status"] != "pending",
        within=300,
        every=0.5,
    )
    write_seconds = time.monotonic() - started
    assert doc["status"] == "ready", doc
    assert doc["version"] == 1 and doc["is_active"]

    resume = doc["content_markdown"]
    # Written by the model about this person, from the profile only.
    assert "Sam Rai" in resume and "Himal Tech" in resume and "Django" in resume
    assert len(resume) > 400
    assert "Acme" not in resume, "The resume names the company being apply to (the prompt says not to)"
    assert "<think>" not in resume and "```" not in resume
    print(
        f"\n[live] posting read in {read_seconds:.1f}s; resume written in {write_seconds:.1f}s "
        f"({len(resume)} characters, {doc['model']}, {doc['generation_ms']} ms in the model)"
    )
