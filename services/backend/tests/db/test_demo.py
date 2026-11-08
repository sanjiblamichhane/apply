"""The demo (John Doe, fictional): at sign-up if asked, and ``apply demo``; an ordinary import, never by accident."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from apply import demo as demo_module
from apply.demo import demo_data, install
from apply.errors import Conflict
from apply.store.sql.models import Application, ApplicationDocument, Match, Profile, User
from tests.conftest import add_account


async def test_the_demo_makes_john_doe_and_signs_in(rt, client):
    report = await install(rt.db, "Demo@Example.com", "a long enough demo password")
    assert report.problems == []
    async with rt.db.transaction() as session:
        user = (await session.execute(select(User).where(User.email == "demo@example.com"))).scalar_one()
        assert user.is_owner
        names = list((await session.execute(select(Profile.name).where(Profile.owner_id == user.id))).scalars())
        assert names == ["John Doe"]
        apps = (await session.execute(select(func.count()).select_from(Application))).scalar_one()
        docs = (await session.execute(select(func.count()).select_from(ApplicationDocument))).scalar_one()
        matches = (await session.execute(select(func.count()).select_from(Match))).scalar_one()
        assert apps == 3 and docs == 4 and matches == 2

    signed = await client.post(
        "/api/v1/auth/sign-in", json={"email": "demo@example.com", "password": "a long enough demo password"}
    )
    assert signed.status_code == 200, signed.text
    board = (await client.get("/api/v1/applications", params={"pack": "job"})).json()["items"]
    assert {a["stage"]["code"] for a in board} == {"new", "in_progress", "interview"}
    inbox = (await client.get("/api/v1/matches", params={"pack": "job"})).json()
    assert [m["score"] for m in inbox["items"]] == [64]  # the tracked one is under Tracked


async def test_the_demo_is_offered_when_an_account_is_made(client):
    made = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "a long enough password here", "demo": True},
    )
    assert made.status_code == 201, made.text
    profiles = (await client.get("/api/v1/profiles")).json()["items"]
    assert [p["name"] for p in profiles] == ["John Doe"]
    assert len((await client.get("/api/v1/applications", params={"pack": "job"})).json()["items"]) == 3


async def test_without_asking_an_account_starts_empty(client):
    made = await client.post(
        "/api/v1/auth/register", json={"email": "plain@example.com", "password": "a long enough password here"}
    )
    assert made.status_code == 201, made.text
    assert (await client.get("/api/v1/profiles")).json()["items"] == []


def test_the_demo_is_looked_for_above_the_package_at_any_depth():
    """In the image the package is at /app/src/apply, with few folders above it: no fixed depth is assumed."""
    here = Path(demo_module.__file__).resolve()
    assert [p.parent.parent for p in demo_module.CANDIDATES[:-1]] == list(here.parents)
    assert len(demo_module.CANDIDATES) == len(here.parents) + 1


def test_the_demo_is_fictional_and_recent():
    data = demo_data()
    text = data.model_dump_json()
    assert "John Doe" in text and "Lorem ipsum" in text
    links = [u for u in text.split('"') if u.startswith("http")]
    assert links and all(".example.com" in u or "//example.com" in u for u in links)
    newest = max(a.created_at for a in data.applications)
    assert newest.date() <= datetime.now(UTC).date()


async def test_the_demo_never_mixes_into_existing_data(rt):
    await add_account(rt, "someone@example.com", "their own long password")
    with pytest.raises(Conflict):
        await install(rt.db, "demo@example.com", "a long enough demo password")
    async with rt.db.transaction() as session:
        assert (await session.execute(select(func.count()).select_from(Profile))).scalar_one() == 0

    # With --force, into the account named, and again adds nothing.
    first = await install(rt.db, "someone@example.com", None, force=True)
    again = await install(rt.db, "someone@example.com", None, force=True)
    assert first.created["profiles"] == 1 and again.created["profiles"] == 0


def test_the_demo_documents_say_only_what_their_profiles_say():
    """Every line of experience in a demo document is in the profile it was written from (no invented claims)."""
    data = demo_data()
    profiles = {p.ref: p for p in data.profiles}
    for app in data.applications:
        for doc in app.documents:
            profile = profiles[doc.profile_ref]
            text = str(profile.attributes) + profile.summary
            for line in doc.content_markdown.splitlines():
                if line.startswith("- "):
                    claim = line[2:].split(":")[0].split(" (")[0]
                    assert any(part.strip() in text for part in claim.split(",")), (doc.ref, line)
