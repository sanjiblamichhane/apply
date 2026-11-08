"""
Finding the models on this machine: local model servers, on one host (the configured model's) and a fixed list of
ports, read-only, never a scan. A server is known by what it answers, not by what it's called:

- ``native``: ``/api/tags`` lists the models (and ``/api/show``, ``/api/ps`` say more about each);
- ``v1``: ``/v1/models`` lists them (and a richer ``/api/v0/models`` catalogue is used where a server has one).

    found = await discover(client, base_url="http://localhost:11434", api="native", ports=[11434, 1234])
"""

import asyncio
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import httpx

Api = Literal["native", "v1"]

# Ports local model servers commonly listen on; Settings → Model looks at these on the configured host.
DEFAULT_PORTS = (11434, 1234, 8080, 1337, 8000)
PROBE_TIMEOUT = 1.5
MAX_MODELS = 100  # per server: a catalogue past this is cut, not a reason to wait


@dataclass(frozen=True)
class FoundModel:
    name: str
    size_bytes: int | None = None
    parameters: str | None = None  # "8.2B"
    family: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    loaded: bool = False
    # Only a model that writes text can be chosen: an embedding model can't answer a prompt.
    usable: bool = True
    note: Literal["embedding"] | None = None


@dataclass(frozen=True)
class Endpoint:
    api: Api
    base_url: str
    version: str | None = None
    models: tuple[FoundModel, ...] = field(default=())


def with_port(base_url: str, port: int) -> str:
    """The configured URL's scheme and host on another port: "http://localhost:11434" → "http://localhost:1234"."""
    parts = urlsplit(base_url)
    host = parts.hostname or "localhost"
    if ":" in host:  # an IPv6 address
        host = f"[{host}]"
    return urlunsplit((parts.scheme or "http", f"{host}:{port}", "", "", ""))


def _clean(base_url: str) -> str:
    parts = urlsplit(base_url.rstrip("/"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


async def _json(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> Any:
    response = await client.request(method, url, timeout=PROBE_TIMEOUT, **kwargs)
    response.raise_for_status()
    return response.json()


async def _native(client: httpx.AsyncClient, base: str) -> Endpoint | None:
    try:
        tags = await _json(client, "GET", f"{base}/api/tags")
        if not isinstance(tags.get("models"), list):
            return None  # something else answers on this port
        listed = [m for m in tags["models"] if isinstance(m, dict) and m.get("name")][:MAX_MODELS]
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    try:
        version = (await _json(client, "GET", f"{base}/api/version")).get("version")
    except (httpx.HTTPError, ValueError, AttributeError):
        version = None
    try:
        loaded = {m.get("name") for m in (await _json(client, "GET", f"{base}/api/ps")).get("models", [])}
    except (httpx.HTTPError, ValueError, AttributeError):
        loaded = set()

    async def show(name: str) -> dict[str, Any]:
        try:
            shown = await _json(client, "POST", f"{base}/api/show", json={"model": name})
            return shown if isinstance(shown, dict) else {}
        except (httpx.HTTPError, ValueError):
            return {}

    shown = await asyncio.gather(*(show(m["name"]) for m in listed))
    models = []
    for item, details in zip(listed, shown, strict=True):
        about = item.get("details") or {}
        capabilities = details.get("capabilities")
        info = details.get("model_info") or {}
        context = next((v for k, v in info.items() if k.endswith(".context_length") and isinstance(v, int)), None)
        embedding = isinstance(capabilities, list) and "completion" not in capabilities
        models.append(
            FoundModel(
                name=item["name"],
                size_bytes=_int(item.get("size")),
                parameters=about.get("parameter_size") or None,
                family=about.get("family") or None,
                quantization=about.get("quantization_level") or None,
                context_length=context,
                loaded=item["name"] in loaded,
                usable=not embedding,
                note="embedding" if embedding else None,
            )
        )
    return Endpoint(api="native", base_url=base, version=version, models=tuple(models))


async def _catalogue(client: httpx.AsyncClient, base: str) -> Endpoint | None:
    """A ``v1`` server's richer catalogue (type, loaded, context), where it has one."""
    try:
        data = (await _json(client, "GET", f"{base}/api/v0/models")).get("data")
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    if not isinstance(data, list):
        return None
    models = tuple(
        FoundModel(
            name=str(m["id"]),
            family=m.get("arch") or None,
            quantization=m.get("quantization") or None,
            context_length=_int(m.get("max_context_length")),
            loaded=m.get("state") == "loaded",
            usable=m.get("type") != "embeddings",
            note="embedding" if m.get("type") == "embeddings" else None,
        )
        for m in data[:MAX_MODELS]
        if isinstance(m, dict) and m.get("id")
    )
    return Endpoint(api="v1", base_url=base, models=models)


async def _v1(client: httpx.AsyncClient, base: str) -> Endpoint | None:
    try:
        data = (await _json(client, "GET", f"{base}/v1/models")).get("data", [])
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    if not isinstance(data, list):
        return None
    if richer := await _catalogue(client, base):
        return richer
    models = []
    for m in data[:MAX_MODELS]:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        embedding = "embed" in str(m["id"]).lower()
        models.append(FoundModel(name=str(m["id"]), usable=not embedding, note="embedding" if embedding else None))
    return Endpoint(api="v1", base_url=base, models=tuple(models))


async def probe(client: httpx.AsyncClient, base_url: str, prefer: Api = "native") -> Endpoint | None:
    """What one server has, in the API it speaks (``prefer`` asked first), or None if no model server answers."""
    base = _clean(base_url)
    first, second = (_native, _v1) if prefer == "native" else (_v1, _native)
    return await first(client, base) or await second(client, base)


async def discover(
    client: httpx.AsyncClient, *, base_url: str, api: Api, ports: tuple[int, ...] | list[int]
) -> list[Endpoint]:
    """
    The servers that answer: the configured one (``base_url``, asked in ``api`` first), and each of ``ports`` on the
    same host. One endpoint per address; the configured one first.
    """
    configured = _clean(base_url)
    wanted = [configured, *(a for a in dict.fromkeys(with_port(configured, p) for p in ports) if a != configured)]
    found = await asyncio.gather(*(probe(client, address, api) for address in wanted))
    return [replace(e, base_url=address) for e, address in zip(found, wanted, strict=True) if e is not None]
