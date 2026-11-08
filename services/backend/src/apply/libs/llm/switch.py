"""
The model in use, as chosen in Settings → Model, or ``.env``'s until then. Each call reads the current choice
(``load``, a small query beside a call of seconds), so a new choice reaches the API and the worker at once, with
no restart. One client per server, sharing one connection pool.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .base import GENERAL, LanguageModel, ModelCheck, Reply, complete_json
from .discover import Api
from .native import NativeConfig, NativeModel
from .v1 import V1Config, V1Model

logger = logging.getLogger("apply.libs.llm")


@dataclass(frozen=True)
class ModelChoice:
    api: Api
    base_url: str
    model: str
    writing_model: str = ""
    num_ctx: int = 16384  # the native API only; a v1 server sets its own where the model is loaded


def client_for(choice: ModelChoice, *, timeout: float, client: httpx.AsyncClient | None = None) -> LanguageModel:
    """A client for one choice. With ``client``, it shares that connection pool (and doesn't close it)."""
    if choice.api == "native":
        return NativeModel(
            NativeConfig(
                base_url=choice.base_url,
                model=choice.model,
                writing_model=choice.writing_model,
                timeout=timeout,
                num_ctx=choice.num_ctx,
            ),
            client=client,
        )
    return V1Model(
        V1Config(
            base_url=choice.base_url,
            model=choice.model,
            writing_model=choice.writing_model,
            timeout=timeout,
        ),
        client=client,
    )


class SwitchableModel:
    def __init__(
        self,
        default: ModelChoice,
        load: Callable[[], Awaitable[ModelChoice | None]],
        *,
        timeout: float,
    ):
        self.default = default
        self._load = load
        self._timeout = timeout
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0), trust_env=False)
        self._clients: dict[ModelChoice, LanguageModel] = {}
        self.last = default

    async def aclose(self) -> None:
        await self._http.aclose()

    async def current(self) -> ModelChoice:
        """The choice in use now: the saved one, else ``.env``'s (also when the database can't be read)."""
        try:
            choice = await self._load() or self.default
        except Exception:  # noqa: BLE001 - a model call shouldn't fail because the choice couldn't be read
            logger.warning("llm: couldn't read the model choice; using the settings'", exc_info=True)
            choice = self.default
        self.last = choice
        return choice

    def client(self, choice: ModelChoice) -> LanguageModel:
        if choice not in self._clients:
            self._clients[choice] = client_for(choice, timeout=self._timeout, client=self._http)
        return self._clients[choice]

    def model_for(self, purpose: str) -> str:
        """The model the last call used for ``purpose`` (what a stored score says wrote it)."""
        return self.client(self.last).model_for(purpose)

    async def chat(
        self,
        prompt: str,
        *,
        purpose: str = GENERAL,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> Reply:
        model = self.client(await self.current())
        return await model.chat(prompt, purpose=purpose, json_schema=json_schema, temperature=temperature)

    async def complete_json(self, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL) -> dict[str, Any]:
        return await complete_json(self, prompt, schema, purpose=purpose)

    async def check(self) -> ModelCheck:
        return await self.client(await self.current()).check()
