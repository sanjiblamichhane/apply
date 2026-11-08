"""
Saved answers to application forms' questions. A pack seeds the common ones; the person adds their own.
Sensitive answers are never sent to a model, and are kept as "decline" until the person says otherwise.
"""

import re
from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument
from apply.packs import get_pack
from apply.store.sql.models import Answer
from apply.store.sql.repo import review as repo

KEY = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


async def add_defaults(session: AsyncSession, owner_id: str, pack: str) -> int:
    """The pack's standard questions the person doesn't have yet. Returns how many were added."""
    have = {a.key for a in await repo.answers(session, owner_id, pack)}
    added = 0
    for position, spec in enumerate(get_pack(pack).standard_questions):
        if spec.key in have:
            continue
        session.add(
            Answer(
                owner_id=owner_id,
                pack=pack,
                key=spec.key,
                question=dict(spec.question),
                answer=spec.default,
                answer_type=spec.answer_type,
                choices=[{"value": v, "label": dict(lbl)} for v, lbl in spec.choices],
                is_sensitive=spec.sensitive,
                source="pack",
                position=position,
            )
        )
        added += 1
    await session.flush()
    return added


def _check(answer_type: str, value: str, choices: list[dict[str, Any]]) -> None:
    if answer_type == "yes_no" and value not in ("", "yes", "no"):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "A yes/no answer is yes or no")
    if answer_type == "choice" and choices and value not in {c["value"] for c in choices} | {""}:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "That isn't one of the choices")
    if answer_type == "url" and value and not re.match(r"^https?://\S+$", value):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "A link starts with http:// or https://")
    if answer_type == "number" and value and not re.match(r"^-?\d+(\.\d+)?$", value):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "That isn't a number")


async def create(
    session: AsyncSession,
    owner_id: str,
    *,
    pack: str,
    key: str,
    question: dict[str, str],
    answer: str,
    answer_type: str,
    is_sensitive: bool,
) -> Answer:
    get_pack(pack)
    if not KEY.match(key):
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "A key is lower-case letters, digits and _")
    _check(answer_type, answer, [])
    row = Answer(
        owner_id=owner_id,
        pack=pack,
        key=key,
        question=_question(question),
        answer=answer,
        answer_type=answer_type,
        is_sensitive=is_sensitive,
        source="user",
        position=1000,
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        raise Conflict(ErrorCode.ANSWER_EXISTS, f"There is already an answer for {key!r}") from None
    return row


def _question(given: dict[str, str]) -> dict[str, str]:
    """A question as typed, in whichever languages it was given. English and Nepali are always filled (with what was
    typed, if not given), as every label has them; another language is there only if given."""
    first = given.get("en") or next((text for text in given.values() if text), "")
    return {**{k: v for k, v in given.items() if v}, "en": first, "ne": given.get("ne") or first}


async def update(session: AsyncSession, owner_id: str, answer_id: str, changes: dict[str, Any]) -> Answer:
    row = await repo.answer(session, owner_id, answer_id, for_update=True)
    if "answer" in changes and changes["answer"] is not None:
        _check(row.answer_type, changes["answer"], row.choices)
        row.answer = changes["answer"]
    if changes.get("question"):
        row.question = {**row.question, **changes["question"]}
    if changes.get("is_sensitive") is not None and row.source == "user":
        row.is_sensitive = bool(changes["is_sensitive"])
    await session.flush()
    return row


async def delete(session: AsyncSession, owner_id: str, answer_id: str) -> None:
    await session.delete(await repo.answer(session, owner_id, answer_id, for_update=True))


async def list_(session: AsyncSession, owner_id: str, pack: str) -> Sequence[Answer]:
    return await repo.answers(session, owner_id, pack)


def recorded(answer: Answer) -> dict[str, Any]:
    """How an answer is kept on a submission: a sensitive one only as provided or declined, never its value."""
    if answer.is_sensitive:
        state = "declined" if answer.answer in ("", "decline") else "provided"
        return {"key": answer.key, "question": answer.question.get("en", ""), "state": state}
    return {
        "key": answer.key,
        "question": answer.question.get("en", ""),
        "state": "provided" if answer.answer else "empty",
        "value": answer.answer,
    }
