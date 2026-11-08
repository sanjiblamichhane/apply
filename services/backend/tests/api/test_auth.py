"""Signing in: the owner account, sessions in cookies, lockout, and cross-site requests refused."""

import subprocess
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from apply.store.sql.models import Session
from tests.conftest import OTHER_EMAIL, OTHER_PASSWORD, OWNER_EMAIL, OWNER_PASSWORD, add_account, make_settings

from .helpers import PROFILE


async def test_init_creates_the_owner_once(rt, pg_url):
    env = {"APPLY_DATABASE_URL": pg_url, "PATH": "/usr/bin:/bin", "APPLY_LANG": "en"}

    def init(email: str, password: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "apply.cli", "init", "--email", email, "--password-stdin"],
            input=password + "\n",
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    short = init("owner@example.com", "short")
    assert short.returncode == 1 and "12 characters" in short.stderr
    made = init("Owner@Example.com", OWNER_PASSWORD)
    assert made.returncode == 0, made.stderr
    assert "owner@example.com" in made.stdout
    again = init("second@example.com", OWNER_PASSWORD)
    assert again.returncode == 1 and "already has an owner" in again.stderr


async def test_sign_in_sets_a_safe_cookie_and_me_answers(client, rt):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    response = await client.post(
        "/api/v1/auth/sign-in", json={"email": " OWNER@example.com ", "password": OWNER_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["email"] == OWNER_EMAIL
    cookie = response.headers["set-cookie"].lower()
    assert "apply_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["is_owner"] is True


async def test_signing_out_ends_the_session(client, owner):
    assert (await client.post("/api/v1/auth/sign-out")).status_code == 204
    client.cookies.clear()
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


async def test_the_old_cookie_is_dead_after_sign_out(client, owner):
    token = client.cookies.get("apply_session")
    await client.post("/api/v1/auth/sign-out")
    client.cookies.set("apply_session", token)
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_wrong_passwords_are_refused_then_lock_the_account(client, rt):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    for _ in range(rt.settings.sign_in_max_failures - 1):
        wrong = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": "nope nope"})
        assert wrong.status_code == 401 and wrong.json()["code"] == "SIGN_IN_FAILED"
    locked = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": "nope nope"})
    assert locked.status_code == 429 and locked.json()["code"] == "SIGN_IN_LOCKED"
    assert int(locked.headers["retry-after"]) > 0
    assert locked.json()["retry_after"] == int(locked.headers["retry-after"])
    # Even the right password waits until the lock ends.
    right = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert right.status_code == 429


async def test_an_unknown_email_gets_the_same_answer(client, rt):
    response = await client.post("/api/v1/auth/sign-in", json={"email": "nobody@example.com", "password": "x" * 12})
    assert response.status_code == 401 and response.json()["code"] == "SIGN_IN_FAILED"


async def test_a_stranger_cant_lock_the_owner_out_of_their_own_browser(client, rt):
    """Security review: a lock only shuts out browsers the account hasn't signed in from."""
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    first = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert first.status_code == 200
    device = client.cookies.get("apply_device")
    assert device and "httponly" in first.headers["set-cookie"].lower()
    await client.post("/api/v1/auth/sign-out")

    # Someone else guesses until the account locks.
    client.cookies.clear()
    for _ in range(rt.settings.sign_in_max_failures):
        await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": "guess guess"})
    stranger = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert stranger.status_code == 429  # a browser it doesn't know waits, even with the right password

    # The owner's own browser still gets in, and keeps its device cookie (no new one is made).
    client.cookies.set("apply_device", device)
    owner = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert owner.status_code == 200
    assert "apply_device" not in owner.headers.get("set-cookie", "")
    # A forged device cookie is no better than none.
    client.cookies.clear()
    for _ in range(rt.settings.sign_in_max_failures):
        await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": "guess guess"})
    client.cookies.set("apply_device", "made-up")
    forged = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert forged.status_code == 429


async def test_a_lock_doesnt_say_whether_an_email_has_an_account(client, rt):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    answers = {}
    for email in (OWNER_EMAIL, "nobody-here@example.com"):
        codes = []
        for _ in range(rt.settings.sign_in_max_failures + 1):
            r = await client.post("/api/v1/auth/sign-in", json={"email": email, "password": "guess guess"})
            codes.append((r.status_code, r.json()["code"]))
        answers[email] = codes
    assert answers[OWNER_EMAIL] == answers["nobody-here@example.com"]
    assert answers[OWNER_EMAIL][-1] == (429, "SIGN_IN_LOCKED")


async def test_a_validation_error_never_echoes_the_password(client):
    response = await client.post("/api/v1/auth/sign-in", json={"email": "a", "password": "my secret password"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "my secret password" not in response.text
    assert response.json()["code"] == "VALIDATION_FAILED"


async def test_cross_site_requests_are_refused(client, owner):
    evil = await client.post("/api/v1/profiles", json={"name": "x"}, headers={"origin": "https://evil.example"})
    assert evil.status_code == 403 and evil.json()["code"] == "ORIGIN_NOT_ALLOWED"
    sneaky = await client.post("/api/v1/profiles", json={"name": "x"}, headers={"sec-fetch-site": "cross-site"})
    assert sneaky.status_code == 403
    web_app = await client.post("/api/v1/profiles", json={"name": "x"}, headers={"origin": "http://localhost:3310"})
    assert web_app.status_code == 201


async def test_an_expired_session_is_refused(client, owner, rt):
    async with rt.db.transaction() as session:
        await session.execute(update(Session).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_everything_but_health_needs_a_session(client):
    assert (await client.get("/api/v1/health")).status_code == 200
    for path in (
        "/api/v1/packs",
        "/api/v1/profiles",
        "/api/v1/opportunities",
        "/api/v1/applications",
        "/api/v1/system/model",
    ):
        response = await client.get(path)
        assert response.status_code == 401, path


def test_cookies_are_secure_and_host_only_beyond_localhost():
    from apply.api.deps import cookie_name

    class Rt:
        settings = make_settings(host="0.0.0.0", allow_remote=True)

    assert cookie_name(Rt()) == "__Host-apply_session"


async def test_the_account_language_can_change(client, owner):
    changed = await client.patch("/api/v1/auth/me", json={"locale": "ne"})
    assert changed.status_code == 200 and changed.json()["locale"] == "ne"
    assert (await client.get("/api/v1/auth/me")).json()["locale"] == "ne"
    bad = await client.patch("/api/v1/auth/me", json={"locale": "fr"})
    assert bad.status_code == 422


async def test_the_first_account_is_the_owners_then_anyone_may_join_until_the_owner_closes_it(client, rt):
    assert (await client.get("/api/v1/auth/setup")).json() == {"open": True, "first_run": True, "mail": False}
    short = await client.post("/api/v1/auth/register", json={"email": "me@example.com", "password": "short"})
    assert short.status_code == 422 and short.json()["code"] == "PASSWORD_TOO_SHORT"
    made = await client.post(
        "/api/v1/auth/register", json={"email": "Me@Example.com", "password": OWNER_PASSWORD, "locale": "ne"}
    )
    assert made.status_code == 201, made.text
    assert made.json()["email"] == "me@example.com" and made.json()["locale"] == "ne" and made.json()["is_owner"]
    assert (await client.get("/api/v1/auth/me")).status_code == 200  # signed in by it
    assert client.cookies.get("apply_device")

    # Then anyone: their own account, not the owner's, and the same email only once.
    assert (await client.get("/api/v1/auth/setup")).json() == {"open": True, "first_run": False, "mail": False}
    owner_cookies = dict(client.cookies)
    client.cookies.clear()
    joined = await client.post("/api/v1/auth/register", json={"email": "sita@example.com", "password": OWNER_PASSWORD})
    assert joined.status_code == 201 and joined.json()["is_owner"] is False
    assert (await client.get("/api/v1/applications")).json()["items"] == []  # their own, empty
    assert (await client.get("/api/v1/people")).json()["code"] == "OWNER_ONLY"
    client.cookies.clear()
    twice = await client.post("/api/v1/auth/register", json={"email": "SITA@example.com", "password": OWNER_PASSWORD})
    assert twice.status_code == 409 and twice.json()["code"] == "EMAIL_TAKEN"

    # The owner closes it: no more accounts; the ones there stay.
    client.cookies.update(owner_cookies)
    closed = await client.put("/api/v1/system/registration", json={"open": False})
    assert closed.json() == {"open": False}
    client.cookies.clear()
    assert (await client.get("/api/v1/auth/setup")).json() == {"open": False, "first_run": False, "mail": False}
    refused = await client.post("/api/v1/auth/register", json={"email": "ram@example.com", "password": OWNER_PASSWORD})
    assert refused.status_code == 403 and refused.json()["code"] == "REGISTRATION_CLOSED"
    signed = await client.post("/api/v1/auth/sign-in", json={"email": "sita@example.com", "password": OWNER_PASSWORD})
    assert signed.status_code == 200


async def test_too_many_new_accounts_from_one_address_wait(client, rt):
    for n in range(5):
        client.cookies.clear()
        made = await client.post(
            "/api/v1/auth/register", json={"email": f"p{n}@example.com", "password": OWNER_PASSWORD}
        )
        assert made.status_code == 201, made.text
    client.cookies.clear()
    sixth = await client.post("/api/v1/auth/register", json={"email": "p6@example.com", "password": OWNER_PASSWORD})
    assert sixth.status_code == 429


async def test_the_owner_turns_an_account_off_and_on_and_deletes_it(client, owner, other_client, rt):
    people = (await client.get("/api/v1/people")).json()["items"]
    assert [p["is_owner"] for p in people] == [True, False]
    me, other = people
    assert set(other) == {"id", "email", "is_owner", "created_at", "last_sign_in_at", "disabled_at"}  # nothing in it

    off = await client.post(f"/api/v1/people/{other['id']}/disable")
    assert off.status_code == 200 and off.json()["disabled_at"]
    assert (await other_client.get("/api/v1/auth/me")).status_code == 401  # signed out at once
    other_client.cookies.clear()
    tried = await other_client.post("/api/v1/auth/sign-in", json={"email": OTHER_EMAIL, "password": OTHER_PASSWORD})
    assert tried.status_code == 403 and tried.json()["code"] == "ACCOUNT_DISABLED"
    wrong = await other_client.post("/api/v1/auth/sign-in", json={"email": OTHER_EMAIL, "password": "wrong password!!"})
    assert wrong.json()["code"] == "SIGN_IN_FAILED"  # off is said only to someone with the password

    assert (await client.post(f"/api/v1/people/{other['id']}/enable")).json()["disabled_at"] is None
    back = await other_client.post("/api/v1/auth/sign-in", json={"email": OTHER_EMAIL, "password": OTHER_PASSWORD})
    assert back.status_code == 200
    await other_client.post("/api/v1/profiles", json=PROFILE)

    for refused in (
        client.post(f"/api/v1/people/{me['id']}/disable"),
        client.delete(f"/api/v1/people/{me['id']}"),
    ):
        assert (await refused).json()["code"] == "ACCOUNT_IS_OWNER"
    assert (await client.delete(f"/api/v1/people/{other['id']}")).status_code == 204
    assert [p["id"] for p in (await client.get("/api/v1/people")).json()["items"]] == [me["id"]]
    assert (await other_client.get("/api/v1/auth/me")).status_code == 401
    assert (await other_client.put("/api/v1/system/model", json={})).status_code in (401, 403)


async def test_only_the_owner_changes_the_installs_model(client, owner, other_client):
    response = await other_client.delete("/api/v1/system/model")
    assert response.status_code == 403 and response.json()["code"] == "OWNER_ONLY"
    assert (await other_client.get("/api/v1/system/model")).status_code == 200  # seen, not changed


async def test_web_setup_can_be_turned_off(rt, pg_url):
    import httpx

    from apply.app import create_app
    from apply.runtime import Runtime

    runtime = Runtime.create(make_settings(database_url=pg_url, web_setup=False))
    app = create_app(runtime=runtime)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8110") as c:
        assert (await c.get("/api/v1/auth/setup")).json() == {"open": False, "first_run": False, "mail": False}
        refused = await c.post("/api/v1/auth/register", json={"email": "me@example.com", "password": OWNER_PASSWORD})
        assert refused.status_code == 409


async def test_registering_from_another_site_is_refused(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": OWNER_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
