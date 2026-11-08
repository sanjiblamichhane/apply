"""
What the browser extension needs to fill an application form: which application the open form is for (by its
URLs), and the fill sheet: the profile's standard values, the saved answers and the documents.

Sensitive answers are in the sheet: they go only into the form the person is looking at, which they submit
themselves. They are never sent to a model (logic/answers).
"""

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, NotFound
from apply.libs.extract import canonical_url
from apply.packs import get_pack
from apply.packs.base import ProfileInput
from apply.store.sql.models import Application, Opportunity
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import documents as documents_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo
from apply.store.sql.repo import review as review_repo

from . import answers as answers_logic

MAX_URLS = 8


def candidates(urls: list[str]) -> list[str]:
    """Each URL as given and canonical, http(s) only, without repeats."""
    out: list[str] = []
    for url in urls[:MAX_URLS]:
        url = url.strip()[:2048]
        if not re.match(r"^https?://", url, re.IGNORECASE):
            continue
        for form in (url, canonical_url(url)):
            if form not in out:
                out.append(form)
    return out


async def lookup(session: AsyncSession, owner_id: str, urls: list[str]) -> tuple[Opportunity, Application | None]:
    """The opportunity behind a form, preferring one already applied to. NOT_FOUND if it isn't tracked."""
    found = await opportunities_repo.by_any_url(session, owner_id, candidates(urls))
    if not found:
        raise NotFound(ErrorCode.OPPORTUNITY_NOT_FOUND, "No opportunity with that address")
    for opp in found:
        application = await applications_repo.by_opportunity(session, owner_id, opp.id)
        if application is not None:
            return opp, await applications_repo.loaded(session, application)
    return found[0], None


def filename(person: str, label: str) -> str:
    """'Sam Rai – Resume.pdf': what the board's reviewer sees, without characters a file name can't hold."""
    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", f"{person} – {label}" if person else label)
    return re.sub(r"\s+", " ", safe).strip()[:120] + ".pdf"


async def sheet(session: AsyncSession, owner_id: str, application_id: str) -> dict[str, Any]:
    application = await applications_repo.get(session, owner_id, application_id)
    opp = await opportunities_repo.get(session, owner_id, application.opportunity_id)
    pack = get_pack(opp.pack)
    profile = None
    if application.profile_id:
        profile = await profiles_repo.get(session, owner_id, application.profile_id)  # SET NULL on delete
    profile = profile or await profiles_repo.default_for(session, owner_id, opp.pack)
    given = ProfileInput(name=profile.name, summary=profile.summary, attributes=profile.attributes) if profile else None
    values = pack.form_values(given) if given else {}
    person = (pack.person_name(given) or given.name) if given else ""
    if not await review_repo.answers(session, owner_id, opp.pack):
        await answers_logic.add_defaults(session, owner_id, opp.pack)
    documents = [
        d
        for d in await documents_repo.of_application(session, owner_id, application_id)
        if d.is_active and d.status == "ready"
    ]
    return {
        "application": await applications_repo.loaded(session, application),
        "opportunity": opp,
        "values": values,
        "answers": await review_repo.answers(session, owner_id, opp.pack),
        "documents": [
            {
                "document_id": d.id,
                "document_type": d.document_type,
                "label": dict(pack.document_type(d.document_type).label),
                "version": d.version,
                "filename": filename(person, pack.document_type(d.document_type).label["en"]),
                "pdf_path": f"/api/v1/applications/{application_id}/documents/{d.id}/pdf",
                "reviewed": d.reviewed_at is not None,
                "open_warnings": sum(1 for w in d.claim_warnings if not w.get("resolved")),
            }
            for d in documents
        ],
    }
