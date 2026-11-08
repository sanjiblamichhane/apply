"""
The live suite: the same journeys against the real model. Skipped unless APPLY_LIVE=1.

    APPLY_LIVE=1 uv run pytest tests/live -s          (or: tests/live.sh from the repo root)

The model is the one named by APPLY_LIVE_LLM_MODEL (required), on a local server speaking the native API at
APPLY_LIVE_LLM_BASE_URL (default http://localhost:11434). The database is still a throwaway one: live means the
model, never your data.
"""

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

from tests.conftest import make_settings, truncate_all

LIVE = os.environ.get("APPLY_LIVE") == "1"
BASE_URL = os.environ.get("APPLY_LIVE_LLM_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("APPLY_LIVE_LLM_MODEL", "")
WRITING_MODEL = os.environ.get("APPLY_LIVE_LLM_WRITING_MODEL", "")


def pytest_collection_modifyitems(config, items):
    if LIVE and MODEL:
        return
    reason = "Name the model: APPLY_LIVE_LLM_MODEL=<name>." if LIVE else "Uses the real model; set APPLY_LIVE=1 to run."
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "tests/live" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture
def live_model():
    from apply.libs.llm import NativeConfig, NativeModel

    return NativeModel(NativeConfig(base_url=BASE_URL, model=MODEL, writing_model=WRITING_MODEL, timeout=300))


@pytest.fixture
async def rt(pg_url, site) -> AsyncIterator[Any]:
    """The runtime on a throwaway database, with the real model."""
    from apply.logic import packs
    from apply.runtime import Runtime

    runtime = Runtime.create(
        make_settings(
            database_url=pg_url,
            llm_base_url=BASE_URL,
            llm_model=MODEL,
            llm_writing_model=WRITING_MODEL,
            llm_timeout=300,
            fetch_allow_private=True,
            worker_poll_seconds=0.2,
        )
    )
    await truncate_all(runtime)
    async with runtime.db.transaction() as session:
        await packs.sync(session)
    yield runtime
    await runtime.aclose()
