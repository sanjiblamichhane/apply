"""
Local models: the v1 client, finding the model servers on this machine, and the switch that
follows Settings → Model. All against fake servers over real HTTP; nothing reaches a real model server.
"""

import socket
from urllib.parse import urlsplit

import httpx
import pytest

from apply.libs.llm import (
    SCORE,
    WRITING,
    LLMError,
    ModelChoice,
    SwitchableModel,
    V1Config,
    V1Model,
    discover,
)
from apply.libs.llm.discover import with_port

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


def v1_client(server, **config) -> V1Model:
    return V1Model(V1Config(base_url=server.url, **({"model": "helper-7b-instruct", "timeout": 5.0} | config)))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ─── the v1 client ───────────────────────────────────────────────────────────


async def test_the_request_holds_the_reply_to_the_schema(v1_server):
    model = v1_client(v1_server)
    reply = await model.chat("Score this", purpose=SCORE, json_schema=SCHEMA)
    body = v1_server.requests[-1]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "reply", "strict": True, "schema": SCHEMA},
    }
    assert body["temperature"] == 0.0 and body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "Score this"}]
    assert reply.text == '{"ok": true}' and reply.model == "helper-7b-instruct"
    await model.aclose()


async def test_writing_uses_the_writing_model_and_a_little_randomness(v1_server):
    v1_server.models.append("helper-14b-instruct")
    model = v1_client(v1_server, writing_model="helper-14b-instruct")
    await model.chat("Write", purpose=WRITING)
    assert v1_server.requests[-1]["model"] == "helper-14b-instruct"
    assert v1_server.requests[-1]["temperature"] == 0.4
    assert "response_format" not in v1_server.requests[-1]
    await model.aclose()


async def test_a_thinking_block_is_dropped_from_the_reply(v1_server):
    v1_server.content = "<think>\nLet me think about it.\n</think>\n\n# The answer"
    model = v1_client(v1_server)
    assert (await model.chat("Write")).text == "# The answer"
    await model.aclose()


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        (lambda s: setattr(s, "models", []), LLMError.MODEL_MISSING),
        (lambda s: setattr(s, "content", "  "), LLMError.EMPTY_REPLY),
        (lambda s: setattr(s, "status", 500), LLMError.UNREACHABLE),
    ],
)
async def test_each_failure_has_the_same_code_as_the_native_clients(v1_server, setup, code):
    setup(v1_server)
    model = v1_client(v1_server)
    with pytest.raises(LLMError) as raised:
        await model.chat("Hello")
    assert raised.value.code == code
    await model.aclose()


async def test_nothing_listening_is_unreachable():
    model = V1Model(V1Config(base_url=f"http://127.0.0.1:{free_port()}", model="m"))
    with pytest.raises(LLMError) as raised:
        await model.chat("Hello")
    assert raised.value.code == LLMError.UNREACHABLE
    await model.aclose()


async def test_the_check_says_which_models_the_server_lacks(v1_server):
    model = v1_client(v1_server, writing_model="gone")
    check = await model.check()
    assert check.reachable and check.missing == ("gone",) and not check.ready
    await model.aclose()


# ─── finding them ────────────────────────────────────────────────────────────


async def test_it_finds_each_server_by_what_it_answers_with_what_it_says_about_its_models(model_server, v1_server):
    model_server.models = ["writer:8b", "embedder:latest"]
    model_server.loaded, model_server.embedding = {"writer:8b"}, {"embedder:latest"}
    async with httpx.AsyncClient() as client:
        found = await discover(
            client, base_url=model_server.url, api="native", ports=[model_server.port, v1_server.port]
        )
    assert [(e.api, e.base_url) for e in found] == [("native", model_server.url), ("v1", v1_server.url)]
    writer, embed = found[0].models
    assert (writer.name, writer.parameters, writer.size_bytes, writer.context_length) == (
        "writer:8b",
        "8.2B",
        5_200_000_000,
        40960,
    )
    assert writer.loaded and writer.usable and writer.family == "writer" and writer.quantization == "Q4_K_M"
    assert not embed.usable and embed.note == "embedding" and not embed.loaded
    assert found[0].version == "0.0.0-fake"
    instruct, embedder = found[1].models
    assert instruct.loaded and instruct.usable and instruct.context_length == 32768
    assert not embedder.usable and embedder.note == "embedding"


async def test_a_v1_server_without_the_richer_catalogue_lists_its_models(v1_server):
    v1_server.catalogue = False
    async with httpx.AsyncClient() as client:
        found = await discover(client, base_url=f"http://127.0.0.1:{free_port()}", api="native", ports=[v1_server.port])
    assert [e.api for e in found] == ["v1"]
    assert [(m.name, m.usable) for m in found[0].models] == [("helper-7b-instruct", True), ("embedder", False)]


async def test_silence_and_things_that_arent_model_servers_are_skipped(site):
    site.add("/v1/models", "<html>a web app, not a model server</html>")
    site.add("/api/tags", '{"unexpected": true}', content_type="application/json")
    async with httpx.AsyncClient() as client:
        # Its /api/tags isn't a model list and its /v1/models isn't JSON; nothing listens on the other port.
        assert await discover(client, base_url=site.url, api="native", ports=[free_port()]) == []
        nowhere = f"http://127.0.0.1:{free_port()}"
        assert await discover(client, base_url=nowhere, api="v1", ports=[urlsplit(site.url).port]) == []


async def test_it_only_looks_on_the_configured_host():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await discover(client, base_url="http://models.lan:11434", api="native", ports=[1234, 8000])
    assert seen and set(seen) == {"models.lan"}


def test_a_port_is_swapped_on_the_same_host():
    assert with_port("http://localhost:11434/", 1234) == "http://localhost:1234"
    assert with_port("http://[::1]:11434", 8080) == "http://[::1]:8080"
    assert with_port("https://models.lan:443/v1", 1337) == "https://models.lan:1337"


# ─── the switch ──────────────────────────────────────────────────────────────


async def test_the_switch_follows_the_choice_at_once_and_falls_back_to_the_settings(model_server, v1_server):
    default = ModelChoice(api="native", base_url=model_server.url, model="writer:8b")
    chosen: list[ModelChoice | None] = [None]

    async def load():
        if chosen[0] == "broken":
            raise RuntimeError("database away")
        return chosen[0]

    model = SwitchableModel(default, load, timeout=5.0)
    await model.chat("one")
    assert len(model_server.requests) == 1 and not v1_server.requests

    chosen[0] = ModelChoice(api="v1", base_url=v1_server.url, model="helper-7b-instruct")
    reply = await model.chat("two", json_schema=SCHEMA)
    assert reply.model == "helper-7b-instruct" and len(v1_server.requests) == 1
    assert model.model_for(SCORE) == "helper-7b-instruct"
    assert (await model.check()).base_url == v1_server.url
    assert model.client(chosen[0]) is model.client(chosen[0])  # one client per choice

    chosen[0] = "broken"  # type: ignore[assignment]
    await model.chat("three")
    assert len(model_server.requests) == 2  # the settings' model, rather than failing the call
    await model.aclose()
