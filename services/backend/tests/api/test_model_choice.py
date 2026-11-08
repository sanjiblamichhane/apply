"""
Settings → Model over the API: what's found on this machine (here, two fake model servers, one per API), choosing
one after a test, and going back to the settings'. A choice reaches the very next model call.
"""

import pytest

from tests.conftest import TEST_API


@pytest.fixture
def both(rt, model_server, v1_server):
    """The native-API server is the configured one; a v1 server answers on one of the ports looked at."""
    model_server.models = ["writer:8b", "writer:14b", "embedder:latest"]
    model_server.loaded, model_server.embedding = {"writer:8b"}, {"embedder:latest"}
    rt.settings.llm_discover_ports = [model_server.port, v1_server.port]
    return model_server, v1_server


async def test_it_lists_what_each_server_has_and_what_is_in_use(client, owner, both):
    model_server, catalogue = both
    found = (await client.get("/api/v1/system/models")).json()
    assert found["current"] == {
        "api": "native",
        "base_url": model_server.url,
        "model": "writer:8b",
        "writing_model": "",
        "num_ctx": 16384,
        "source": "settings",
    }
    assert [(e["api"], e["base_url"]) for e in found["endpoints"]] == [
        ("native", model_server.url),
        ("v1", catalogue.url),
    ]
    writer = found["endpoints"][0]["models"][0]
    assert writer == {
        "name": "writer:8b",
        "size_bytes": 5_200_000_000,
        "parameters": "8.2B",
        "family": "writer",
        "quantization": "Q4_K_M",
        "context_length": 40960,
        "loaded": True,
        "usable": True,
        "note": None,
    }
    assert found["endpoints"][0]["models"][2]["usable"] is False


async def test_choosing_a_model_tests_it_saves_it_and_the_next_call_uses_it(client, owner, both, rt):
    _native, catalogue = both
    chosen = await client.put("/api/v1/system/model", json={"base_url": catalogue.url, "model": "helper-7b-instruct"})
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["current"] == {
        "api": "v1",
        "base_url": catalogue.url,
        "model": "helper-7b-instruct",
        "writing_model": "",
        "num_ctx": None,
        "source": "chosen",
    }
    assert catalogue.requests[-1]["response_format"]["type"] == "json_schema"  # the test

    await rt.model.chat("Write something")
    assert catalogue.requests[-1]["messages"][0]["content"] == "Write something"
    status = (await client.get("/api/v1/system/model")).json()
    assert status["base_url"] == catalogue.url and status["ready"]


async def test_a_native_choice_keeps_its_writing_model_and_context(client, owner, both, rt):
    model_server, _ = both
    chosen = await client.put(
        "/api/v1/system/model",
        json={"base_url": model_server.url, "model": "writer:8b", "writing_model": "writer:14b", "num_ctx": 32768},
    )
    assert chosen.status_code == 200, chosen.text
    assert {r["model"] for r in model_server.requests} == {"writer:8b", "writer:14b"}  # both were tested
    await rt.model.chat("Write", purpose="writing")
    assert model_server.requests[-1]["model"] == "writer:14b"
    assert model_server.requests[-1]["options"]["num_ctx"] == 32768


@pytest.mark.parametrize(
    "body",
    [
        {"base_url": "http://127.0.0.1:9", "model": "writer:8b"},  # nothing found there
        {"base_url": "NATIVE", "model": "llama9:400b"},  # not on that server
        {"base_url": "NATIVE", "model": "embedder:latest"},  # an embedding model can't write
        {"base_url": "NATIVE", "model": "writer:8b", "writing_model": "gone"},
    ],
)
async def test_only_a_usable_model_just_found_can_be_chosen(client, owner, both, body):
    model_server, _ = both
    body = {k: (model_server.url if v == "NATIVE" else v) for k, v in body.items()}
    refused = await client.put("/api/v1/system/model", json=body)
    assert refused.status_code == 422 and refused.json()["code"] == "MODEL_NOT_FOUND"
    assert (await client.get("/api/v1/system/models")).json()["current"]["source"] == "settings"


async def test_a_model_that_fails_the_test_is_not_chosen(client, owner, both, rt):
    model_server, catalogue = both
    catalogue.content = "Sure! Here's your JSON: ok"
    refused = await client.put("/api/v1/system/model", json={"base_url": catalogue.url, "model": "helper-7b-instruct"})
    assert refused.status_code == 422
    assert refused.json()["code"] == "MODEL_TEST_FAILED"
    assert refused.json()["reason"] == "LLM_BAD_REPLY" and refused.json()["model"] == "helper-7b-instruct"
    assert (await client.get("/api/v1/system/models")).json()["current"]["source"] == "settings"
    before = len(model_server.requests)
    await rt.model.chat("still the settings' model")
    assert len(model_server.requests) == before + 1


async def test_going_back_to_the_settings(client, owner, both, rt):
    model_server, catalogue = both
    await client.put("/api/v1/system/model", json={"base_url": catalogue.url, "model": "helper-7b-instruct"})
    reset = await client.delete("/api/v1/system/model")
    assert reset.status_code == 200 and reset.json()["source"] == "settings"
    before = len(model_server.requests)
    await rt.model.chat("hello")
    assert len(model_server.requests) == before + 1


async def test_only_the_signed_in_owner_sees_or_changes_the_model(client, both):
    _, catalogue = both
    assert (await client.get("/api/v1/system/models")).status_code == 401
    put = await client.put(
        "/api/v1/system/model",
        json={"base_url": catalogue.url, "model": "helper-7b-instruct"},
        headers={"Origin": TEST_API},
    )
    assert put.status_code == 401
