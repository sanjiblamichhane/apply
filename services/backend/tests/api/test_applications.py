"""Applications over HTTP: into the pipeline's first stage, moved through it, with history; one per opportunity."""

from .helpers import POSTING, PROFILE


async def make(client) -> tuple[dict, dict]:
    profile = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    opp = (await client.post("/api/v1/opportunities", json={"text": POSTING})).json()
    return profile, opp


async def test_a_new_application_starts_in_the_first_stage(client, owner):
    profile, opp = await make(client)
    response = await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})
    assert response.status_code == 201, response.text
    app = response.json()
    assert app["stage"]["code"] == "new" and app["stage"]["category"] == "active"
    assert app["profile_id"] == profile["id"]  # the default profile
    assert app["opportunity"]["id"] == opp["id"]
    history = (await client.get(f"/api/v1/applications/{app['id']}/history")).json()["items"]
    assert [h["stage"]["code"] for h in history] == ["new"] and history[0]["exited_at"] is None


async def test_moving_through_the_pipeline_keeps_its_history(client, owner):
    _, opp = await make(client)
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    for code in ("screening", "interview", "declined"):
        moved = await client.post(
            f"/api/v1/applications/{app['id']}/stage", json={"stage_code": code, "note": f"to {code}"}
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()["stage"]["code"] == code
    history = (await client.get(f"/api/v1/applications/{app['id']}/history")).json()["items"]
    assert [h["stage"]["code"] for h in history] == ["declined", "interview", "screening", "new"]
    assert [h["outcome"] for h in history[1:]] == ["reject", "advance", "advance"]
    assert history[0]["exited_at"] is None and all(h["exited_at"] for h in history[1:])
    same = await client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": "declined"})
    assert same.status_code == 200
    assert len((await client.get(f"/api/v1/applications/{app['id']}/history")).json()["items"]) == 4


async def test_an_unknown_stage_is_refused(client, owner):
    _, opp = await make(client)
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    response = await client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": "hired_twice"})
    assert response.status_code == 422 and response.json()["code"] == "STAGE_NOT_FOUND"


async def test_one_application_per_opportunity(client, owner):
    _, opp = await make(client)
    first = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    again = await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})
    assert again.status_code == 409
    assert again.json()["code"] == "APPLICATION_EXISTS" and again.json()["application_id"] == first["id"]


async def test_listing_and_filtering_by_stage(client, owner):
    ids = []
    for i in range(3):
        opp = (await client.post("/api/v1/opportunities", json={"text": f"Role {i}\n{POSTING}"})).json()
        ids.append((await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()["id"])
    await client.post(f"/api/v1/applications/{ids[0]}/stage", json={"stage_code": "interview"})
    everything = (await client.get("/api/v1/applications")).json()["items"]
    assert [a["id"] for a in everything] == list(reversed(ids))
    interviewing = (await client.get("/api/v1/applications", params={"pack": "job", "stage": "interview"})).json()
    assert [a["id"] for a in interviewing["items"]] == [ids[0]]


async def test_notes_and_the_profile_can_change(client, owner):
    profile, opp = await make(client)
    other = (await client.post("/api/v1/profiles", json=PROFILE | {"name": "Other"})).json()
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    changed = await client.patch(
        f"/api/v1/applications/{app['id']}", json={"notes": "Referred by Asha", "profile_id": other["id"]}
    )
    assert changed.json()["notes"] == "Referred by Asha" and changed.json()["profile_id"] == other["id"]


async def test_another_account_gets_not_found(client, owner, other_client):
    _, opp = await make(client)
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    for call in (
        other_client.get(f"/api/v1/applications/{app['id']}"),
        other_client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": "offer"}),
        other_client.get(f"/api/v1/applications/{app['id']}/history"),
        other_client.delete(f"/api/v1/applications/{app['id']}"),
        other_client.post("/api/v1/applications", json={"opportunity_id": opp["id"]}),
    ):
        assert (await call).status_code == 404


async def test_the_packs_endpoint_describes_the_job_pack_in_every_language(client, owner):
    pack = (await client.get("/api/v1/packs/job")).json()
    assert pack["label"] == {"en": "Jobs", "ne": "जागिर", "es": "Empleos"}
    assert [s["code"] for s in pack["pipeline"]["stages"]][:2] == ["new", "in_progress"]
    assert {d["key"] for d in pack["document_types"] if d["generatable"]} == {"resume", "cover_letter"}
    assert pack["profile_schema"]["properties"]["experience"]
    assert pack["category_labels"]["success"]["ne"]
    assert (await client.get("/api/v1/packs/visa")).json()["code"] == "PACK_NOT_FOUND"


async def test_deleting_an_application_keeps_its_posting_and_it_can_be_tracked_again(client, owner):
    _, opp = await make(client)
    app = (await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})).json()
    await client.post(f"/api/v1/applications/{app['id']}/stage", json={"stage_code": "screening"})
    assert (await client.delete(f"/api/v1/applications/{app['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/applications/{app['id']}")).status_code == 404
    assert app["id"] not in [a["id"] for a in (await client.get("/api/v1/applications")).json()["items"]]
    assert (await client.get(f"/api/v1/opportunities/{opp['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/applications/{app['id']}")).status_code == 404
    again = await client.post("/api/v1/applications", json={"opportunity_id": opp["id"]})
    assert again.status_code == 201 and again.json()["stage"]["code"] == "new"
