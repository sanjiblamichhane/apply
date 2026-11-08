"""Profiles over HTTP: create, read, change, delete; fields held to the pack; one default per pack."""

from .helpers import PROFILE


async def test_create_read_change_delete(client, owner):
    made = await client.post("/api/v1/profiles", json=PROFILE)
    assert made.status_code == 201, made.text
    profile = made.json()
    assert profile["is_default"] is True  # the first one is the default
    assert profile["attributes"]["experience"][0]["organisation"] == "Himal Tech"

    got = await client.get(f"/api/v1/profiles/{profile['id']}")
    assert got.json() == profile

    changed = await client.patch(
        f"/api/v1/profiles/{profile['id']}", json={"name": "Backend (2026)", "tone_instructions": "Plain and warm"}
    )
    assert changed.status_code == 200
    assert changed.json()["name"] == "Backend (2026)" and changed.json()["tone_instructions"] == "Plain and warm"
    assert changed.json()["attributes"] == profile["attributes"]

    listed = await client.get("/api/v1/profiles", params={"pack": "job"})
    assert [p["id"] for p in listed.json()["items"]] == [profile["id"]]

    assert (await client.delete(f"/api/v1/profiles/{profile['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/profiles/{profile['id']}")).status_code == 404


async def test_fields_that_dont_fit_the_pack_are_refused_with_where(client, owner):
    bad = await client.post("/api/v1/profiles", json=PROFILE | {"attributes": {"skills": "not a list"}})
    assert bad.status_code == 422
    body = bad.json()
    assert body["code"] == "INVALID_ATTRIBUTES" and body["errors"][0]["loc"] == ["skills"]
    unknown_pack = await client.post("/api/v1/profiles", json=PROFILE | {"pack": "visa"})
    assert unknown_pack.status_code == 404 and unknown_pack.json()["code"] == "PACK_NOT_FOUND"
    wrong_kind = await client.post("/api/v1/profiles", json=PROFILE | {"kind": "organisation"})
    assert wrong_kind.status_code == 422
    extra = await client.post("/api/v1/profiles", json=PROFILE | {"owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})
    assert extra.status_code == 422 and extra.json()["code"] == "VALIDATION_FAILED"


async def test_one_default_per_pack(client, owner):
    first = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    second = (await client.post("/api/v1/profiles", json=PROFILE | {"name": "Data", "is_default": True})).json()
    assert second["is_default"]
    assert not (await client.get(f"/api/v1/profiles/{first['id']}")).json()["is_default"]
    # Deleting the default hands it on.
    await client.delete(f"/api/v1/profiles/{second['id']}")
    assert (await client.get(f"/api/v1/profiles/{first['id']}")).json()["is_default"]


async def test_another_account_gets_not_found(client, owner, other_client):
    profile = (await client.post("/api/v1/profiles", json=PROFILE)).json()
    for call in (
        other_client.get(f"/api/v1/profiles/{profile['id']}"),
        other_client.patch(f"/api/v1/profiles/{profile['id']}", json={"name": "mine now"}),
        other_client.delete(f"/api/v1/profiles/{profile['id']}"),
    ):
        response = await call
        assert response.status_code == 404 and response.json()["code"] == "PROFILE_NOT_FOUND"
    assert (await other_client.get("/api/v1/profiles")).json()["items"] == []


async def test_pages(client, owner):
    ids = [(await client.post("/api/v1/profiles", json=PROFILE | {"name": f"P{i}"})).json()["id"] for i in range(5)]
    first = (await client.get("/api/v1/profiles", params={"limit": 2})).json()
    second = (await client.get("/api/v1/profiles", params={"limit": 2, "after": first["next_cursor"]})).json()
    third = (await client.get("/api/v1/profiles", params={"limit": 2, "after": second["next_cursor"]})).json()
    seen = [p["id"] for page in (first, second, third) for p in page["items"]]
    assert seen == list(reversed(ids)) and third["next_cursor"] is None
