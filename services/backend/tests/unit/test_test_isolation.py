"""The tests can't reach your development database or bucket: the environment and .env are ignored."""

import os

from tests.conftest import make_settings


def test_no_apply_variable_reaches_the_tests():
    assert not [n for n in os.environ if n.startswith("APPLY_") and not n.startswith("APPLY_LIVE")]


def test_test_settings_ignore_the_environment_and_dot_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APPLY_DATABASE_URL=postgresql+asyncpg://me:secret@127.0.0.1:54329/apply\n")
    monkeypatch.setenv("APPLY_DATABASE_URL", "postgresql+asyncpg://me:secret@127.0.0.1:54329/apply")
    settings = make_settings(database_url="postgresql+asyncpg://test@127.0.0.1:1/throwaway")
    assert settings.database_url.endswith("/throwaway")


def test_test_settings_never_point_at_the_development_bucket(monkeypatch):
    monkeypatch.setenv("APPLY_STORAGE_ENDPOINT", "http://127.0.0.1:4443")
    assert make_settings().storage_endpoint == "http://127.0.0.1:9"
