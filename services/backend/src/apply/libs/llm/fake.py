"""A model for tests of the logic that calls one: scripted replies, every prompt kept."""

from collections.abc import Callable
from typing import Any

from .base import GENERAL, LLMError, ModelCheck, Reply, complete_json

Responder = Callable[[str, str, dict[str, Any] | None], str]


class FakeModel:
    def __init__(self, responder: Responder | None = None, *, model: str = "fake"):
        self.responder = responder or (lambda prompt, purpose, schema: "{}" if schema else "ok")
        self.model = model
        self.prompts: list[tuple[str, str]] = []
        self.error: LLMError | None = None

    def model_for(self, purpose: str) -> str:
        return self.model

    async def chat(
        self,
        prompt: str,
        *,
        purpose: str = GENERAL,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> Reply:
        self.prompts.append((purpose, prompt))
        if self.error is not None:
            raise self.error
        return Reply(text=self.responder(prompt, purpose, json_schema), model=self.model, milliseconds=1)

    async def complete_json(self, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL) -> dict[str, Any]:
        return await complete_json(self, prompt, schema, purpose=purpose)

    async def check(self) -> ModelCheck:
        return ModelCheck(reachable=True, base_url="fake://", wanted=(self.model,), installed=(self.model,))
