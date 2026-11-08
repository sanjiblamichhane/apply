"""
Real HTTP servers for tests, each in its own thread on a random port of 127.0.0.1:

- ``FakeNativeServer`` answers /api/chat, /api/version, /api/tags, /api/ps and /api/show as a native-API model
  server does, from a responder the test sets, and keeps every request body (so a test can check think, format,
  num_ctx…);
- ``FakeV1Server`` answers /v1/models and /v1/chat/completions as a v1-API model server does, and the richer
  /api/v0/models catalogue when ``catalogue`` is set;
- ``Site`` serves pages a test registers (JSON-LD postings, walls, redirects, big or odd responses).
"""

import asyncio
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


class ServerThread:
    def __init__(self, app: Any):
        self.server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off", access_log=False)
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> "ServerThread":
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("test server did not start")
            time.sleep(0.01)
        return self

    @property
    def port(self) -> int:
        return self.server.servers[0].sockets[0].getsockname()[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


# ─── a fake model server ───────────────────────────────────────────────────────────

Responder = Callable[[dict[str, Any]], str]


def schema_example(schema: dict[str, Any]) -> Any:
    """A value that fits a (simple) JSON schema: what a well-behaved model would send."""
    kind = schema.get("type")
    if "enum" in schema:
        return schema["enum"][-1]
    if kind == "object":
        return {k: schema_example(v) for k, v in schema.get("properties", {}).items()}
    if kind == "array":
        return [schema_example(schema.get("items", {"type": "string"}))]
    if kind == "integer":
        return schema.get("minimum", 0) + 80 if schema.get("maximum", 100) >= 80 else schema.get("minimum", 0)
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    return "example"


def default_responder(body: dict[str, Any]) -> str:
    if "format" in body:
        return json.dumps(schema_example(body["format"]))
    return "# A document\n\nWritten by the fake model."


@dataclass
class FakeNativeServer:
    models: list[str] = field(default_factory=lambda: ["writer:8b"])
    requests: list[dict[str, Any]] = field(default_factory=list)
    responder: Responder = default_responder
    status: int = 200  # anything else: the server answering with an error
    delay: float = 0.0  # seconds before answering (timeouts)
    raw: str | None = None  # a body to send as it is (unparseable replies)
    loaded: set[str] = field(default_factory=set)  # what /api/ps lists
    embedding: set[str] = field(default_factory=set)  # models whose capabilities are embedding only

    def reset(self) -> None:
        self.requests.clear()
        self.responder = default_responder
        self.status, self.delay, self.raw = 200, 0.0, None
        self.models = ["writer:8b"]
        self.loaded, self.embedding = set(), set()

    def app(self) -> Starlette:
        async def chat(request: Request) -> Response:
            body = await request.json()
            self.requests.append(body)
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.raw is not None:
                return Response(self.raw, media_type="application/json")
            if self.status != 200:
                return JSONResponse({"error": "fake failure"}, status_code=self.status)
            if body.get("model") not in self.models:
                return JSONResponse({"error": f"model '{body.get('model')}' not found"}, status_code=404)
            content = self.responder(body)
            return JSONResponse(
                {"model": body["model"], "message": {"role": "assistant", "content": content}, "done": True}
            )

        async def version(_request: Request) -> Response:
            return JSONResponse({"version": "0.0.0-fake"})

        async def tags(_request: Request) -> Response:
            return JSONResponse(
                {
                    "models": [
                        {
                            "name": m,
                            "size": 5_200_000_000,
                            "details": {"family": "writer", "parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
                        }
                        for m in self.models
                    ]
                }
            )

        async def ps(_request: Request) -> Response:
            return JSONResponse({"models": [{"name": m} for m in self.models if m in self.loaded]})

        async def show(request: Request) -> Response:
            name = (await request.json()).get("model")
            if name not in self.models:
                return JSONResponse({"error": "not found"}, status_code=404)
            capabilities = ["embedding"] if name in self.embedding else ["completion", "tools"]
            return JSONResponse({"capabilities": capabilities, "model_info": {"writer.context_length": 40960}})

        return Starlette(
            routes=[
                Route("/api/chat", chat, methods=["POST"]),
                Route("/api/version", version),
                Route("/api/tags", tags),
                Route("/api/ps", ps),
                Route("/api/show", show, methods=["POST"]),
            ]
        )

    @property
    def prompts(self) -> list[str]:
        return [r["messages"][0]["content"] for r in self.requests]


def v1_responder(body: dict[str, Any]) -> str:
    if "response_format" in body:
        return json.dumps(schema_example(body["response_format"]["json_schema"]["schema"]))
    return "A reply."


@dataclass
class FakeV1Server:
    """A local v1-API model server. ``catalogue``: also the richer /api/v0/models."""

    models: list[str] = field(default_factory=lambda: ["helper-7b-instruct", "embedder"])
    requests: list[dict[str, Any]] = field(default_factory=list)
    responder: Responder = field(default=lambda body: v1_responder(body))
    catalogue: bool = True
    status: int = 200
    content: str | None = None  # a reply to send as it is (thinking, empty, not JSON)

    def reset(self) -> None:
        self.requests.clear()
        self.models = ["helper-7b-instruct", "embedder"]
        self.responder = v1_responder
        self.catalogue, self.status, self.content = True, 200, None

    def app(self) -> Starlette:
        async def chat(request: Request) -> Response:
            body = await request.json()
            self.requests.append(body)
            if self.status != 200:
                return JSONResponse({"error": "fake failure"}, status_code=self.status)
            if body.get("model") not in self.models:
                return JSONResponse({"error": {"message": f"model {body.get('model')} not found"}}, status_code=404)
            content = self.content if self.content is not None else self.responder(body)
            return JSONResponse({"choices": [{"message": {"role": "assistant", "content": content}}]})

        async def models(_request: Request) -> Response:
            return JSONResponse({"object": "list", "data": [{"id": m, "object": "model"} for m in self.models]})

        async def v0(_request: Request) -> Response:
            if not self.catalogue:
                return Response("not here", status_code=404)
            return JSONResponse(
                {
                    "data": [
                        {
                            "id": m,
                            "type": "embeddings" if "embed" in m else "llm",
                            "arch": "helper",
                            "quantization": "Q4_K_M",
                            "state": "loaded" if i == 0 else "not-loaded",
                            "max_context_length": 32768,
                        }
                        for i, m in enumerate(self.models)
                    ]
                }
            )

        return Starlette(
            routes=[
                Route("/v1/chat/completions", chat, methods=["POST"]),
                Route("/v1/models", models),
                Route("/api/v0/models", v0),
            ]
        )


# ─── a small web site ────────────────────────────────────────────────────────


@dataclass
class Page:
    body: bytes | str = ""
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Site:
    pages: dict[str, Page] = field(default_factory=dict)
    hits: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def reset(self) -> None:
        self.pages.clear()
        self.hits.clear()

    def add(self, path: str, body: bytes | str = "", **kwargs: Any) -> None:
        self.pages[path] = Page(body=body, **kwargs)

    def app(self) -> Any:
        async def asgi(scope: dict[str, Any], receive: Any, send: Any) -> None:
            path = scope["path"] + (f"?{scope['query_string'].decode()}" if scope.get("query_string") else "")
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            self.hits.append((path, headers))
            page = self.pages.get(path) or self.pages.get(scope["path"])
            if page is None:
                response = Response("not here", status_code=404)
            else:
                body = page.body.encode() if isinstance(page.body, str) else page.body
                response = Response(
                    body, status_code=page.status, headers={"content-type": page.content_type, **page.headers}
                )
            await response(scope, receive, send)

        return asgi
