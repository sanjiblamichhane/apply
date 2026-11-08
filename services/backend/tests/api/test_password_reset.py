"""Forgotten passwords: a link by email, the same answer for any email, used once, and everyone signed out."""

import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import pytest
from sqlalchemy import select, update

from apply.libs import mail
from apply.store.sql.models import PasswordReset, User
from tests.conftest import OTHER_EMAIL, OTHER_PASSWORD, OWNER_EMAIL, OWNER_PASSWORD, add_account

NEW_PASSWORD = "a brand new long password"


@pytest.fixture
def outbox(rt, monkeypatch) -> list[EmailMessage]:
    """Mail as it would go to the SMTP server, kept here instead."""
    sent: list[EmailMessage] = []
    monkeypatch.setattr(rt.settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(rt.settings, "public_url", "https://apply.example.org")
    monkeypatch.setattr(mail, "deliver", lambda _settings, message: sent.append(message))
    return sent


def token_in(message: EmailMessage) -> str:
    body = message.get_content()
    found = re.search(r"https://apply\.example\.org/reset-password\?token=([\w-]+)", body)
    assert found, body
    return found.group(1)


async def forgot(client, email: str):
    return await client.post("/api/v1/auth/forgot-password", json={"email": email})


async def test_a_link_by_email_sets_a_new_password_and_signs_out_everywhere(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    signed_in = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    old_cookie = signed_in.cookies.get("apply_session")

    assert (await forgot(client, " Owner@Example.com ")).status_code == 202
    assert len(outbox) == 1
    message = outbox[0]
    assert message["To"] == OWNER_EMAIL and message["Subject"] == "Reset your apply password"
    assert message["Auto-Submitted"] == "auto-generated"
    assert "It works once, for 30 minutes." in message.get_content()
    token = token_in(message)

    # Only the hash is kept.
    async with rt.db.transaction() as session:
        stored = (await session.execute(select(PasswordReset.token_hash))).scalars().all()
    assert len(stored) == 1 and token not in stored[0]

    check = await client.post("/api/v1/auth/reset-password/check", json={"token": token})
    assert check.status_code == 200 and check.json() == {"email": OWNER_EMAIL}

    short = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "short"})
    assert short.status_code == 422 and short.json()["code"] == "PASSWORD_TOO_SHORT"

    done = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert done.status_code == 204

    # Whoever had the old session is out; the old password no longer works, the new one does.
    client.cookies.set("apply_session", old_cookie)
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    client.cookies.clear()
    old = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert old.status_code == 401
    new = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": NEW_PASSWORD})
    assert new.status_code == 200

    # Used once.
    again = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert again.status_code == 404 and again.json()["code"] == "RESET_LINK_INVALID"
    check = await client.post("/api/v1/auth/reset-password/check", json={"token": token})
    assert check.status_code == 404 and check.json()["code"] == "RESET_LINK_INVALID"


async def test_the_same_answer_for_an_email_with_no_account_and_nothing_sent(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    response = await forgot(client, "nobody@example.com")
    known = await forgot(client, OWNER_EMAIL)
    assert response.status_code == known.status_code == 202
    assert response.content == known.content
    assert [m["To"] for m in outbox] == [OWNER_EMAIL]


async def test_a_turned_off_account_gets_no_link_and_its_links_stop_working(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    await add_account(rt, OTHER_EMAIL, OTHER_PASSWORD)
    await forgot(client, OTHER_EMAIL)
    token = token_in(outbox[0])
    async with rt.db.transaction() as session:
        await session.execute(update(User).where(User.email == OTHER_EMAIL).values(disabled_at=datetime.now(UTC)))
    assert (await forgot(client, OTHER_EMAIL)).status_code == 202
    assert len(outbox) == 1
    used = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert used.status_code == 404 and used.json()["code"] == "RESET_LINK_INVALID"


async def test_a_link_expires(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    await forgot(client, OWNER_EMAIL)
    token = token_in(outbox[0])
    async with rt.db.transaction() as session:
        await session.execute(update(PasswordReset).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    response = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert response.status_code == 404 and response.json()["code"] == "RESET_LINK_INVALID"


async def test_a_new_password_uses_up_the_other_links_and_lifts_a_lock(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    await forgot(client, OWNER_EMAIL)
    await forgot(client, OWNER_EMAIL)
    first, second = token_in(outbox[0]), token_in(outbox[1])
    async with rt.db.transaction() as session:
        await session.execute(
            update(User).values(locked_until=datetime.now(UTC) + timedelta(minutes=10), failed_sign_ins=3)
        )
    assert (
        await client.post("/api/v1/auth/reset-password", json={"token": second, "password": NEW_PASSWORD})
    ).status_code == 204
    other = await client.post("/api/v1/auth/reset-password", json={"token": first, "password": NEW_PASSWORD})
    assert other.status_code == 404
    signed_in = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": NEW_PASSWORD})
    assert signed_in.status_code == 200


async def test_an_inbox_and_the_server_cant_be_flooded(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    answers = [(await forgot(client, OWNER_EMAIL)).status_code for _ in range(5)]
    assert answers == [202] * 5
    assert len(outbox) == 3  # an account gets at most 3 an hour; the answer doesn't say
    limited = await forgot(client, OWNER_EMAIL)  # one address: 5 requests an hour
    assert limited.status_code == 429 and limited.headers["retry-after"] == "3600"


async def test_the_email_is_in_the_accounts_language(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    async with rt.db.transaction() as session:
        await session.execute(update(User).values(locale="es"))
    await forgot(client, OWNER_EMAIL)
    assert outbox[0]["Subject"] == "Restablezca su contraseña de apply"
    assert "Funciona una vez, durante 30 minutos." in outbox[0].get_content()


async def test_a_link_is_the_web_apps_address_never_the_requests_host(client, rt, outbox):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    await client.post(
        "/api/v1/auth/forgot-password", json={"email": OWNER_EMAIL}, headers={"x-forwarded-host": "evil.example"}
    )
    body = outbox[0].get_content()
    assert "evil.example" not in body and "https://apply.example.org/reset-password?token=" in body


async def test_an_email_that_cant_be_sent_is_logged_and_the_answer_is_the_same(client, rt, outbox, monkeypatch, caplog):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)

    def refuse(_settings, _message):
        raise ConnectionRefusedError("no SMTP server here")

    monkeypatch.setattr(mail, "deliver", refuse)
    assert (await forgot(client, OWNER_EMAIL)).status_code == 202
    assert "Couldn't send a password reset email" in caplog.text


async def test_with_no_email_set_up_it_says_so(client, rt):
    setup = await client.get("/api/v1/auth/setup")
    assert setup.json()["mail"] is False
    response = await forgot(client, OWNER_EMAIL)
    assert response.status_code == 409 and response.json()["code"] == "MAIL_NOT_SET_UP"


async def test_setup_says_when_email_can_be_sent(client, rt, outbox):
    assert (await client.get("/api/v1/auth/setup")).json()["mail"] is True


async def test_apply_password_sets_one_from_the_command_line(client, rt, pg_url):
    await add_account(rt, OWNER_EMAIL, OWNER_PASSWORD)
    await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    env = {"APPLY_DATABASE_URL": pg_url, "PATH": "/usr/bin:/bin", "APPLY_LANG": "en"}

    def password(email: str, secret: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "apply.cli", "password", "--email", email, "--password-stdin"],
            input=secret + "\n",
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    assert "12 characters" in password(OWNER_EMAIL, "short").stderr
    missing = password("nobody@example.com", NEW_PASSWORD)
    assert missing.returncode == 1 and "no account for nobody@example.com" in missing.stderr
    done = password(OWNER_EMAIL.upper(), NEW_PASSWORD)
    assert done.returncode == 0 and "signed out everywhere" in done.stdout
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    signed_in = await client.post("/api/v1/auth/sign-in", json={"email": OWNER_EMAIL, "password": NEW_PASSWORD})
    assert signed_in.status_code == 200
