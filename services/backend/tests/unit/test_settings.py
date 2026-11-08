"""Settings: safe defaults, bound to this machine, Postgres only."""

import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_the_defaults_run_on_this_machine():
    s = make_settings()
    assert s.host == "127.0.0.1" and s.port == 8110
    assert s.llm_base_url == "http://localhost:11434" and s.llm_model == "writer:8b"
    assert s.llm_num_ctx == 16384
    assert not s.fetch_allow_private
    assert not s.secure_cookies  # plain http on localhost; Secure everywhere else


def test_binding_beyond_this_machine_needs_saying_so():
    with pytest.raises(ValidationError, match="APPLY_ALLOW_REMOTE"):
        make_settings(host="0.0.0.0")
    s = make_settings(host="0.0.0.0", allow_remote=True)
    assert s.secure_cookies


def test_postgres_only():
    with pytest.raises(ValidationError, match="Postgres only"):
        make_settings(database_url="sqlite+aiosqlite:///x.db")


def test_the_example_password_is_refused():
    with pytest.raises(ValidationError, match="changeme"):
        make_settings(database_url="postgresql+asyncpg://apply:changeme@postgres:5432/apply")
    make_settings(database_url="postgresql+asyncpg://apply:9f3c2a@postgres:5432/apply")


def test_the_web_app_and_the_api_are_the_origins_allowed():
    origins = make_settings().own_origins
    assert "http://localhost:3310" in origins and "http://127.0.0.1:8110" in origins
    assert "http://evil.example" not in origins
