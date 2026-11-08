"""
A model on a local server that speaks the ``native`` API (``/api/chat``).

Not the server's ``/v1`` endpoint, because only the native one takes the three options that matter:

- ``think: false``: a reasoning model otherwise reasons out loud first, which is slow and ends up in the reply;
- ``format``: a JSON schema the reply is held to, so a small model's JSON always parses;
- ``num_ctx``: the context size. The usual default is a few thousand tokens, and it drops the start of a longer
  prompt without saying so.
"""

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .base import GENERAL, WRITING, LLMError, ModelCheck, Reply, complete_json


@dataclass(frozen=True)
class NativeConfig:
    base_url: str = "http://localhost:11434"
    model: str = ""
    writing_model: str = ""
    timeout: float = 180.0
    num_ctx: int = 16384


class NativeModel:
    def __init__(self, config: NativeConfig, *, client: httpx.AsyncClient | None = None):
        self.config = config
        self._base = config.base_url.rstrip("/")
        # One client per process: connections are reused. trust_env=False: a proxy set for the shell must not
        # see prompts, which carry people's profiles.
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(config.timeout, connect=5.0), trust_env=False)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def model_for(self, purpose: str) -> str:
        if purpose == WRITING and self.config.writing_model:
            return self.config.writing_model
        return self.config.model

    async def chat(
        self,
        prompt: str,
        *,
        purpose: str = GENERAL,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> Reply:
        """
        One prompt in, the reply text out. With ``json_schema`` the reply is JSON matching it; parsing is the
        caller's (or ``complete_json``'s) job, so an unexpected reply can still be logged.
        """
        if temperature is None:
            temperature = 0.4 if purpose == WRITING else 0.0
        model = self.model_for(purpose)
        if not model:
            raise LLMError(LLMError.MODEL_MISSING, "no model chosen yet: choose one in Settings → Model")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "options": {"temperature": temperature, "num_ctx": self.config.num_ctx},
        }
        if json_schema is not None:
            body["format"] = json_schema

        started = time.monotonic()
        try:
            response = await self._client.post(f"{self._base}/api/chat", json=body)
        except httpx.TimeoutException as exc:
            raise LLMError(LLMError.TIMEOUT, f"{model} took longer than {self.config.timeout:.0f}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(LLMError.UNREACHABLE, f"model server unreachable at {self._base}: {exc!r}") from exc

        if response.status_code == 404:
            raise LLMError(LLMError.MODEL_MISSING, f"the model server at {self._base} has no model {model}")
        if response.status_code >= 400:
            raise LLMError(LLMError.UNREACHABLE, f"model server answered {response.status_code}: {response.text[:300]}")
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(LLMError.BAD_REPLY, f"unexpected reply from the model server: {exc!r}") from exc

        text = (content or "").strip()
        if not text:
            raise LLMError(LLMError.EMPTY_REPLY, f"{model} gave an empty reply")
        return Reply(text=text, model=model, milliseconds=int((time.monotonic() - started) * 1000))

    async def complete_json(self, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL) -> dict[str, Any]:
        return await complete_json(self, prompt, schema, purpose=purpose)

    async def check(self) -> ModelCheck:
        """Is the server there, and does it have the configured models?"""
        wanted = tuple(dict.fromkeys(m for m in (self.config.model, self.config.writing_model) if m))
        try:
            version = (await self._client.get(f"{self._base}/api/version", timeout=5.0)).json().get("version")
            tags = (await self._client.get(f"{self._base}/api/tags", timeout=5.0)).json()
        except (httpx.HTTPError, ValueError) as exc:
            return ModelCheck(
                reachable=False, base_url=self._base, wanted=wanted, error=repr(exc), num_ctx=self.config.num_ctx
            )
        installed = tuple(sorted(m.get("name", "") for m in tags.get("models", [])))
        missing = tuple(m for m in wanted if m not in installed and f"{m}:latest" not in installed)
        return ModelCheck(
            reachable=True,
            base_url=self._base,
            version=version,
            wanted=wanted,
            installed=installed,
            missing=missing,
            num_ctx=self.config.num_ctx,
        )
