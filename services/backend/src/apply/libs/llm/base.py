"""The interface every model client keeps, its reply and its errors."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("apply.libs.llm")

# What a prompt is for. Writing (prose a person reads) may use a larger model and a little randomness;
# everything else (scores, checks, extraction) uses none, so the same question gets the same answer.
WRITING = "writing"
SCORE = "score"
CHECK = "check"
GENERAL = "general"


class LLMError(Exception):
    """
    The model could not be reached or gave an unusable reply. ``code`` is stable (callers store it and the web
    app translates it); the message is for logs.
    """

    UNREACHABLE = "LLM_UNREACHABLE"
    TIMEOUT = "LLM_TIMEOUT"
    BAD_REPLY = "LLM_BAD_REPLY"
    EMPTY_REPLY = "LLM_EMPTY_REPLY"
    MODEL_MISSING = "LLM_MODEL_MISSING"

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    @property
    def retryable(self) -> bool:
        """Worth asking again in a while: the server was away or slow, not wrong."""
        return self.code in (self.UNREACHABLE, self.TIMEOUT)


@dataclass(frozen=True)
class Reply:
    text: str
    model: str
    milliseconds: int


@dataclass(frozen=True)
class ModelCheck:
    reachable: bool
    base_url: str
    version: str | None = None
    wanted: tuple[str, ...] = ()
    installed: tuple[str, ...] = ()
    num_ctx: int | None = None
    error: str | None = None
    missing: tuple[str, ...] = field(default=())

    @property
    def ready(self) -> bool:
        return self.reachable and not self.missing


class LanguageModel(Protocol):
    async def chat(
        self,
        prompt: str,
        *,
        purpose: str = GENERAL,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> Reply: ...

    async def check(self) -> ModelCheck: ...

    def model_for(self, purpose: str) -> str: ...

    async def complete_json(self, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL) -> dict[str, Any]: ...


async def complete_json(
    model: LanguageModel, prompt: str, schema: dict[str, Any], *, purpose: str = GENERAL
) -> dict[str, Any]:
    """
    ``chat`` for structured answers, parsed. One retry on a reply that does not parse, then give up loudly: a
    caller scoring a job records "not scored" rather than inventing a number.
    """
    last: Exception | None = None
    for _attempt in range(2):
        reply = await model.chat(prompt, purpose=purpose, json_schema=schema)
        try:
            value = json.loads(reply.text)
        except json.JSONDecodeError as exc:
            last = exc
            logger.warning("llm: unparseable JSON for %s from %s", purpose, reply.model)
            continue
        if isinstance(value, dict):
            return value
        last = TypeError(f"expected an object, got {type(value).__name__}")
    raise LLMError(LLMError.BAD_REPLY, f"No usable JSON after a retry: {last}")
