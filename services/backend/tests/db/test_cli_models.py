"""`apply models` and `apply check-model`: what's on this machine, and the model in use (chosen, or .env's)."""

import argparse

from apply import cli
from apply.i18n import t
from tests.conftest import make_settings


def test_models_lists_each_server_and_what_is_in_use(monkeypatch, capsys, pg_url, model_server, v1_server):
    model_server.models, model_server.loaded = ["writer:8b"], {"writer:8b"}
    settings = make_settings(database_url=pg_url, llm_base_url=model_server.url, llm_discover_ports=[v1_server.port])
    monkeypatch.setattr(cli, "_settings", lambda: settings)
    monkeypatch.setenv("APPLY_LANG", "en")
    assert cli.cmd_models(argparse.Namespace()) == 0
    out = capsys.readouterr().out
    assert t("models.in_use.settings", model="writer:8b", url=model_server.url) in out
    assert f"{model_server.url}  [native]" in out and f"{v1_server.url}  [v1]" in out
    assert "writer:8b  8.2B · 5.2 GB · 40,960 ctx · loaded" in out
    assert "embedder  32,768 ctx · embeddings only: can't be chosen" in out


def test_models_says_what_to_start_when_nothing_answers(monkeypatch, capsys, pg_url):
    settings = make_settings(database_url=pg_url, llm_base_url="http://127.0.0.1:9")
    monkeypatch.setattr(cli, "_settings", lambda: settings)
    monkeypatch.setenv("APPLY_LANG", "en")
    assert cli.cmd_models(argparse.Namespace()) == 1
    assert t("models.none") in capsys.readouterr().out


def test_check_model_checks_the_model_in_use(monkeypatch, capsys, pg_url, model_server):
    settings = make_settings(database_url=pg_url, llm_base_url=model_server.url)
    monkeypatch.setattr(cli, "_settings", lambda: settings)
    monkeypatch.setenv("APPLY_LANG", "en")
    assert cli.cmd_check_model(argparse.Namespace()) == 0
    assert "writer:8b ready" in capsys.readouterr().out
