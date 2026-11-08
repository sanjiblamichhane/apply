"""
A model on a local server that speaks the ``v1`` API (``/v1/chat/completions``).

- ``/v1/chat/completions`` with ``response_format: json_schema`` (strict), so the reply is held to the schema, as
  the native API's ``format`` does;
- a ``<think>…</think>`` block reasoning models write first is dropped from the reply;
- the context size is the server's (set where the model is loaded), so there's no ``num_ctx`` to send.
"""

import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .base import GENERAL, WRITING, LLMError, ModelCheck, Reply, complete_json

THINKING = re.compile(r"^\s*<think>.*?</think>\s*", re.S)


@dataclass(frozen=True)
class V1Config:
    base_url: str = "http://localhost:1234"
    model: str = ""
    writing_model: str = ""
    timeout: float = 180.0


class V1Model:
    def __init__(self, config: V1Config, *, client: httpx.AsyncClient | None = None):
        self.config = config
        self._base = config.base_url.rstrip("/")
        # trust_env=False: a proxy set for the shell must not see prompts, which carry people's profiles.
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
        if temperature is None:
            temperature = 0.4 if purpose == WRITING else 0.0
        model = self.model_for(purpose)
        if not model:
            raise LLMError(LLMError.MODEL_MISSING, "no model chosen yet: choose one in Settings → Model")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
        }
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "reply", "strict": True, "schema": json_schema},
            }

        started = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._base}/v1/chat/completions", json=body, timeout=self.config.timeout
            )
        except httpx.TimeoutException as exc:
            raise LLMError(LLMError.TIMEOUT, f"{model} took longer than {self.config.timeout:.0f}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(LLMError.UNREACHABLE, f"model server unreachable at {self._base}: {exc!r}") from exc

        if response.status_code == 404 or (response.status_code == 400 and "not found" in response.text.lower()):
            raise LLMError(LLMError.MODEL_MISSING, f"the model server at {self._base} has no model {model}")
        if response.status_code >= 400:
            raise LLMError(LLMError.UNREACHABLE, f"model server answered {response.status_code}: {response.text[:300]}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(LLMError.BAD_REPLY, f"unexpected reply from the model server: {exc!r}") from exc

        text = THINKING.sub("", content or "").strip()
        if not text:
            raise LLMError(LLMError.EMPTY_REPLY, f"{model} gave an empty reply")
        return Reply(text=text, model=model, milliseconds=int((time.monotonic() - started) * 1000))

    async def complete_json(self, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL) -> dict[str, Any]:
        return await complete_json(self, prompt, schema, purpose=purpose)

    async def check(self) -> ModelCheck:
        """Is the server there, and does it have the chosen models?"""
        wanted = tuple(dict.fromkeys(m for m in (self.config.model, self.config.writing_model) if m))
        try:
            listed = (await self._client.get(f"{self._base}/v1/models", timeout=5.0)).json()
            installed = tuple(sorted(str(m["id"]) for m in listed.get("data", []) if isinstance(m, dict) and "id" in m))
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            return ModelCheck(reachable=False, base_url=self._base, wanted=wanted, error=repr(exc))
        missing = tuple(m for m in wanted if m not in installed)
        return ModelCheck(reachable=True, base_url=self._base, wanted=wanted, installed=installed, missing=missing)
