"""
Which model apply uses: found on this machine (libs/llm/discover), chosen in Settings → Model after a test, and
read on every call (libs/llm/switch). Until one is chosen, or after "Use .env settings", it's the settings'.

A choice must be a server just found (the configured host, the fixed ports: never an address from a request)
and a model it lists that can write text; and each chosen model must give a usable answer to a short JSON
prompt. Otherwise nothing changes.
"""

import json
from dataclasses import dataclass, replace
from typing import Literal

import httpx

from apply.errors import ErrorCode, InvalidArgument
from apply.libs.llm import CHECK, Endpoint, LLMError, ModelChoice, client_for, discover
from apply.settings import AppSettings
from apply.store.sql import Database
from apply.store.sql.repo import model_choice as repo

TEST_PROMPT = 'Reply with this JSON object and nothing else: {"ok": true}'
TEST_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


@dataclass(frozen=True)
class Current:
    choice: ModelChoice
    source: Literal["chosen", "settings"]


def from_settings(settings: AppSettings) -> ModelChoice:
    return ModelChoice(
        api=settings.llm_api,
        base_url=settings.llm_base_url.rstrip("/"),
        model=settings.llm_model,
        writing_model=settings.llm_writing_model,
        num_ctx=settings.llm_num_ctx,
    )


async def load(db: Database) -> ModelChoice | None:
    """The saved choice, or None (then the settings' is used)."""
    async with db.transaction() as session:
        row = await repo.get(session)
        if row is None:
            return None
        return ModelChoice(
            api="native" if row.api == "native" else "v1",
            base_url=row.base_url,
            model=row.model,
            writing_model=row.writing_model,
            num_ctx=row.num_ctx,
        )


async def current(db: Database, settings: AppSettings) -> Current:
    saved = await load(db)
    if saved:
        return Current(choice=saved, source="chosen")
    return Current(choice=from_settings(settings), source="settings")


async def find(settings: AppSettings, *, client: httpx.AsyncClient | None = None) -> list[Endpoint]:
    """Every model server that answers on this machine, and its models."""
    own = client is None
    http = client or httpx.AsyncClient(trust_env=False, follow_redirects=False)
    try:
        return await discover(
            http, base_url=settings.llm_base_url, api=settings.llm_api, ports=settings.llm_discover_ports
        )
    finally:
        if own:
            await http.aclose()


@dataclass(frozen=True)
class Tested:
    current: Current
    milliseconds: int


async def choose(
    db: Database,
    settings: AppSettings,
    *,
    base_url: str,
    model: str,
    writing_model: str = "",
    num_ctx: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> Tested:
    found = await find(settings, client=client)
    endpoint = next((e for e in found if e.base_url == base_url.rstrip("/")), None)
    if endpoint is None:
        raise InvalidArgument(ErrorCode.MODEL_NOT_FOUND, "No model server answers at that address now")
    usable = {m.name for m in endpoint.models if m.usable}
    for name in filter(None, (model, writing_model)):
        if name not in usable:
            raise InvalidArgument(
                ErrorCode.MODEL_NOT_FOUND, f"the server at {endpoint.base_url} has no usable model {name!r}"
            )
    if writing_model == model:
        writing_model = ""
    choice = ModelChoice(
        api=endpoint.api,
        base_url=endpoint.base_url,
        model=model,
        writing_model=writing_model,
        num_ctx=num_ctx or settings.llm_num_ctx,
    )

    # Each chosen model must answer a short JSON prompt (the first call also loads it, which can take a while).
    milliseconds = 0
    for name in filter(None, (model, writing_model)):
        milliseconds += await _test(replace(choice, model=name, writing_model=""), llm_timeout=settings.llm_timeout)

    async with db.transaction() as session:
        await repo.put(
            session,
            api=choice.api,
            base_url=choice.base_url,
            model=choice.model,
            writing_model=choice.writing_model,
            num_ctx=choice.num_ctx,
        )
    return Tested(current=Current(choice=choice, source="chosen"), milliseconds=milliseconds)


async def _test(choice: ModelChoice, *, llm_timeout: float) -> int:
    """How long the model took to give a usable JSON answer; MODEL_TEST_FAILED (with why) if it didn't."""
    tester = client_for(choice, timeout=llm_timeout)
    try:
        reply = await tester.chat(TEST_PROMPT, purpose=CHECK, json_schema=TEST_SCHEMA)
        if not isinstance(json.loads(reply.text), dict):
            raise LLMError(LLMError.BAD_REPLY, "the reply isn't a JSON object")
        return reply.milliseconds
    except (LLMError, ValueError) as exc:
        reason = exc.code if isinstance(exc, LLMError) else LLMError.BAD_REPLY
        raise InvalidArgument(
            ErrorCode.MODEL_TEST_FAILED,
            f"{choice.model} failed the test: {exc}",
            extra={"reason": reason, "model": choice.model},
        ) from exc
    finally:
        close = getattr(tester, "aclose", None)
        if close is not None:
            await close()


async def reset(db: Database, settings: AppSettings) -> Current:
    async with db.transaction() as session:
        await repo.clear(session)
    return Current(choice=from_settings(settings), source="settings")
