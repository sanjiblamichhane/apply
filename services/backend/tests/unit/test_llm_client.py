"""The native-API client against a fake model server over real HTTP: what it sends, and how every failure comes back."""

import json

import httpx
import pytest

from apply.libs.llm import GENERAL, SCORE, WRITING, LLMError, NativeConfig, NativeModel


def client(model_server, **config) -> NativeModel:
    return NativeModel(NativeConfig(base_url=model_server.url, **({"model": "writer:8b", "timeout": 5.0} | config)))


async def test_the_request_turns_thinking_off_holds_to_the_schema_and_sets_the_context(model_server):
    model = client(model_server, num_ctx=16384)
    schema = {"type": "object", "properties": {"fit_score": {"type": "integer"}}, "required": ["fit_score"]}
    await model.chat("Score this", purpose=SCORE, json_schema=schema)
    body = model_server.requests[-1]
    assert body["think"] is False
    assert body["stream"] is False
    assert body["format"] == schema
    assert body["options"] == {"temperature": 0.0, "num_ctx": 16384}
    assert body["messages"] == [{"role": "user", "content": "Score this"}]
    assert body["model"] == "writer:8b"
    await model.aclose()


async def test_writing_gets_a_little_randomness_and_the_writing_model_when_there_is_one(model_server):
    model_server.models = ["writer:8b", "writer:14b"]
    model = client(model_server, writing_model="writer:14b")
    reply = await model.chat("Write", purpose=WRITING)
    assert model_server.requests[-1]["options"]["temperature"] == 0.4
    assert model_server.requests[-1]["model"] == "writer:14b" == reply.model
    await model.chat("Check", purpose=GENERAL)
    assert model_server.requests[-1]["model"] == "writer:8b"
    assert model_server.requests[-1]["options"]["temperature"] == 0.0
    assert "format" not in model_server.requests[-1]
    await model.aclose()


async def test_the_reply_text_is_trimmed_and_timed(model_server):
    model_server.responder = lambda body: "  # Resume\n\n"
    model = client(model_server)
    reply = await model.chat("Write", purpose=WRITING)
    assert reply.text == "# Resume"
    assert reply.milliseconds >= 0
    await model.aclose()


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        (lambda o: setattr(o, "responder", lambda body: "   "), LLMError.EMPTY_REPLY),
        (lambda o: setattr(o, "raw", "not json at all"), LLMError.BAD_REPLY),
        (lambda o: setattr(o, "raw", json.dumps({"message": {}})), LLMError.BAD_REPLY),
        (lambda o: setattr(o, "status", 500), LLMError.UNREACHABLE),
        (lambda o: setattr(o, "models", ["llama3.2:latest"]), LLMError.MODEL_MISSING),
    ],
)
async def test_each_failure_has_its_code(model_server, setup, code):
    setup(model_server)
    model = client(model_server)
    with pytest.raises(LLMError) as caught:
        await model.chat("Hello")
    assert caught.value.code == code
    await model.aclose()


async def test_a_slow_model_times_out_with_its_code(model_server):
    model_server.delay = 1.0
    model = client(model_server, timeout=0.2)
    with pytest.raises(LLMError) as caught:
        await model.chat("Hello")
    assert caught.value.code == LLMError.TIMEOUT
    assert caught.value.retryable
    await model.aclose()


async def test_nothing_listening_is_unreachable():
    model = NativeModel(NativeConfig(base_url="http://127.0.0.1:9", model="writer:8b", timeout=2))
    with pytest.raises(LLMError) as caught:
        await model.chat("Hello")
    assert caught.value.code == LLMError.UNREACHABLE
    await model.aclose()


async def test_complete_json_retries_an_unparseable_reply_once(model_server):
    replies = iter(["{not json", json.dumps({"fit_score": 91})])
    model_server.responder = lambda body: next(replies)
    model = client(model_server)
    assert await model.complete_json("Score", {"type": "object"}) == {"fit_score": 91}
    assert len(model_server.requests) == 2
    await model.aclose()


async def test_complete_json_gives_up_after_the_retry_rather_than_inventing_a_value(model_server):
    model_server.responder = lambda body: "[1, 2, 3]"
    model = client(model_server)
    with pytest.raises(LLMError) as caught:
        await model.complete_json("Score", {"type": "object"})
    assert caught.value.code == LLMError.BAD_REPLY
    assert len(model_server.requests) == 2
    await model.aclose()


async def test_the_check_says_which_models_are_missing(model_server):
    model_server.models = ["writer:8b"]
    model = client(model_server, writing_model="writer:14b")
    check = await model.check()
    assert check.reachable and not check.ready
    assert check.missing == ("writer:14b",)
    assert check.version == "0.0.0-fake"
    await model.aclose()


async def test_the_check_reports_an_unreachable_server():
    model = NativeModel(NativeConfig(base_url="http://127.0.0.1:9"))
    check = await model.check()
    assert not check.reachable and not check.ready
    await model.aclose()


async def test_no_proxy_from_the_environment_sees_prompts(model_server, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    model = client(model_server)
    assert (await model.chat("Hello")).text
    await model.aclose()


async def test_a_shared_client_is_left_open(model_server):
    shared = httpx.AsyncClient()
    model = NativeModel(NativeConfig(base_url=model_server.url), client=shared)
    await model.aclose()
    assert not shared.is_closed
    await shared.aclose()
