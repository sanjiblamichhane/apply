"""
Fixtures for every suite.

The database and bucket are always throwaway ones started here (compose.test.yml as the named project
apply-test-backend: no anonymous container or volume), and the database is migrated with the real migrations.
Nothing in the tests reads APPLY_DATABASE_URL or a .env file: every APPLY_* variable but APPLY_LIVE* is
removed before any test runs, and settings are built from the stack's URLs only, so a test can never reach your
development database or bucket, even by mistake (tests/unit/test_test_isolation.py checks).

Unit tests use none of the database fixtures, so they run without a container engine.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from sqlalchemy import text

# ── isolation: before anything imports apply's settings ────────────────────
for _name in [n for n in os.environ if n.startswith("APPLY_") and not n.startswith("APPLY_LIVE")]:
    del os.environ[_name]

from apply.settings import AppSettings  # noqa: E402

from .support.servers import FakeNativeServer, FakeV1Server, ServerThread, Site  # noqa: E402

TEST_API = "http://127.0.0.1:8110"
OWNER_EMAIL, OWNER_PASSWORD = "owner@example.com", "correct horse battery staple"
OTHER_EMAIL, OTHER_PASSWORD = "someone.else@example.com", "another long password"


def make_settings(**overrides: Any) -> AppSettings:
    """
    Settings for a test: no .env, no environment, only what is passed (and the defaults). Looking for model
    servers stays on the configured URL, so no test ever reaches a model server running on this machine; the file
    bucket is nowhere (port 9) unless a test passes the throwaway one, so none reaches compose's emulator either.
    """
    return AppSettings(
        _env_file=None,
        env="test",
        **({"llm_discover_ports": [], "llm_model": "writer:8b", "storage_endpoint": "http://127.0.0.1:9"} | overrides),
    )


# ── servers ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def _native_server() -> Iterator[tuple[FakeNativeServer, ServerThread]]:
    fake = FakeNativeServer()
    server = ServerThread(fake.app()).start()
    yield fake, server
    server.stop()


@pytest.fixture
def model_server(_native_server) -> FakeNativeServer:
    fake, server = _native_server
    fake.reset()
    fake.url = server.url  # type: ignore[attr-defined]
    fake.port = server.port  # type: ignore[attr-defined]
    return fake


@pytest.fixture(scope="session")
def _v1_server() -> Iterator[tuple[FakeV1Server, ServerThread]]:
    fake = FakeV1Server()
    server = ServerThread(fake.app()).start()
    yield fake, server
    server.stop()


@pytest.fixture
def v1_server(_v1_server) -> FakeV1Server:
    """A local server speaking the v1 API (with the richer /api/v0 catalogue unless ``catalogue`` is turned off)."""
    fake, server = _v1_server
    fake.reset()
    fake.url = server.url  # type: ignore[attr-defined]
    fake.port = server.port  # type: ignore[attr-defined]
    return fake


@pytest.fixture(scope="session")
def _site_server() -> Iterator[tuple[Site, ServerThread]]:
    site = Site()
    server = ServerThread(site.app()).start()
    yield site, server
    server.stop()


@pytest.fixture
def site(_site_server) -> Site:
    found, server = _site_server
    found.reset()
    found.url = server.url  # type: ignore[attr-defined]
    return found


# ── the throwaway database ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def _stack() -> Iterator[Any]:
    """The suite's throwaway Postgres and bucket: compose.test.yml as project apply-test-backend, all named."""
    from .support.stack import Stack

    with Stack("apply-test-backend") as stack:
        yield stack


@pytest.fixture(scope="session")
def pg_url(_stack) -> str:
    from apply.store.sql import migrate

    migrate(_stack.database_url)
    return _stack.database_url


@pytest.fixture(scope="session")
def storage_url(_stack) -> str:
    """A throwaway storage emulator, like the database: never a real bucket."""
    return _stack.storage_url


async def truncate_all(rt) -> None:
    from apply.store.sql.models import Base

    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with rt.db.engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    await rt.files.ensure()
    await rt.files.delete_prefix("")


@pytest.fixture
async def rt(pg_url, storage_url, model_server, site) -> AsyncIterator[Any]:
    """A runtime on the throwaway database and bucket, the fake model server, and fetching from the test site."""
    from apply.logic import packs
    from apply.runtime import Runtime

    runtime = Runtime.create(
        make_settings(
            source_base_urls={
                kind: site.url for kind in ("board01", "board02", "board03", "contracts_finder", "grants_gov")
            },
            database_url=pg_url,
            storage_endpoint=storage_url,
            storage_bucket="apply-test",
            llm_base_url=model_server.url,
            llm_timeout=5,
            fetch_allow_private=True,
            fetch_timeout=5,
            worker_poll_seconds=0.05,
            scheduler_tick_seconds=0.2,
            auto_poll_seconds=0.05,
        )
    )
    await truncate_all(runtime)
    async with runtime.db.transaction() as session:
        await packs.sync(session)
    yield runtime
    await runtime.aclose()


@pytest.fixture
async def client(rt) -> AsyncIterator[httpx.AsyncClient]:
    """The API, in-process through ASGI, with its start-up and shut-down run as uvicorn would."""
    from apply.app import create_app

    app = create_app(runtime=rt, close_runtime=False)  # the rt fixture closes it
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=TEST_API) as c:
            yield c


async def add_account(rt, email: str, password: str) -> None:
    """The owner through `apply init`'s path; any later account directly (init makes only one)."""
    from apply.logic.auth import create_owner, hash_password
    from apply.store.sql.models import User
    from apply.store.sql.repo import users

    async with rt.db.transaction() as session:
        has_owner = await users.owner_exists(session)
    if not has_owner:
        await create_owner(rt.db, email, password)
        return
    async with rt.db.transaction() as session:
        session.add(User(email=email, password_hash=await hash_password(password), is_owner=False))


async def sign_in(
    client: httpx.AsyncClient, rt, email: str = OWNER_EMAIL, password: str = OWNER_PASSWORD, *, create: bool = True
) -> dict:
    if create:
        await add_account(rt, email, password)
    response = await client.post("/api/v1/auth/sign-in", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def owner(client, rt) -> dict:
    """The client, signed in as the owner."""
    return await sign_in(client, rt)


@pytest.fixture
async def other_client(rt, client) -> AsyncIterator[httpx.AsyncClient]:
    """A second, separate browser signed in as a different account."""
    from apply.app import create_app

    app = create_app(runtime=rt, close_runtime=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=TEST_API) as c:
        await sign_in(c, rt, OTHER_EMAIL, OTHER_PASSWORD)
        yield c


@pytest.fixture
async def worker(rt) -> AsyncIterator[Any]:
    """The real worker loop, running in the background on every queue, as `apply worker` runs it."""
    from apply.logic.background import QUEUES
    from apply.worker import build

    w = build(rt, queues=list(QUEUES), concurrency=1, name="test-worker")
    stop = asyncio.Event()
    task = asyncio.create_task(w.run_forever(stop))
    yield w
    stop.set()
    await asyncio.wait_for(task, timeout=30)


async def poll(client: httpx.AsyncClient, path: str, done, *, within: float = 30.0, every: float = 0.05) -> dict:
    """GET ``path`` until ``done(body)`` is true (as the web app polls), or fail after ``within`` seconds."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + within
    while True:
        response = await client.get(path)
        assert response.status_code == 200, response.text
        body = response.json()
        if done(body):
            return body
        if loop.time() > deadline:
            raise AssertionError(f"{path} did not settle in {within}s: {body}")
        await asyncio.sleep(every)
