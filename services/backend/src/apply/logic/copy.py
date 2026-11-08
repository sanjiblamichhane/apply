"""
The extension's copy panel: a profile's values, ready to paste into any form, and the pack's saved answers.

Nothing here touches a web page. The panel shows each value, and a click puts it on the clipboard; the person
pastes it. Sensitive answers (equal-opportunity questions) are marked, and the panel shows them only after "Show".
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, NotFound
from apply.packs import DEFAULT_PACK, get_pack
from apply.packs.base import COPY_TABS, CopyGroup, CopyItem, CopyTab, ProfileInput
from apply.store.sql.models import Answer, Profile
from apply.store.sql.repo import profiles as profiles_repo
from apply.store.sql.repo import review as review_repo


@dataclass(frozen=True)
class CopySheet:
    profile: Profile | None
    profiles: list[Profile]
    tabs: list[CopyTab]


def answer_text(answer: Answer) -> str:
    """A saved answer as a form wants it: Yes / No, a choice's words, or the text."""
    if answer.answer_type == "yes_no":
        return {"yes": "Yes", "no": "No"}.get(answer.answer, "")
    if answer.answer_type == "choice":
        for choice in answer.choices or []:
            if isinstance(choice, dict) and choice.get("value") == answer.answer:
                found: Any = choice.get("label") or {}
                return str(found.get("en") or answer.answer) if isinstance(found, dict) else str(found)
        return answer.answer if answer.answer not in ("decline",) else ""
    return answer.answer


async def sheet(session: AsyncSession, owner_id: str, profile_id: str | None, pack: str | None) -> CopySheet:
    """The chosen profile (else the pack's default, else the newest) as copy tabs, and the profiles to choose from."""
    pack_key = pack or DEFAULT_PACK
    choices, _ = await profiles_repo.list_(session, owner_id, pack=None, after=None, limit=100)
    profiles = list(choices)
    if profile_id:
        profile = await profiles_repo.get(session, owner_id, profile_id)
    else:
        profile = await profiles_repo.default_for(session, owner_id, pack_key)
        if profile is None:
            profile = next((p for p in profiles if p.pack == pack_key), profiles[0] if profiles else None)
    if profile is None:
        return CopySheet(None, profiles, [])
    try:
        spec = get_pack(profile.pack)
    except NotFound as exc:  # a pack no longer installed
        raise NotFound(ErrorCode.PROFILE_NOT_FOUND, "This profile's pack isn't installed") from exc
    tabs = spec.copy_sheet(ProfileInput(name=profile.name, summary=profile.summary, attributes=profile.attributes))
    answers = [
        CopyItem(dict(a.question), text, sensitive=a.is_sensitive)
        for a in await review_repo.answers(session, owner_id, profile.pack)
        if (text := answer_text(a).strip())
    ]
    if answers:
        tabs.append(CopyTab("answers", COPY_TABS["answers"], [CopyGroup("", answers)]))
    return CopySheet(profile, profiles, tabs)
