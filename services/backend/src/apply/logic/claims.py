"""
The claim check: what in a written document the profile doesn't back up, for the person to fix or confirm.

Two parts, because a small model's prompt alone doesn't stop it embellishing:

- **rules** (deterministic): every ``[CONFIRM: …]`` marker the writer left, and every number or percentage
  that isn't in the profile ("led a team of 12", "cut costs 30%");
- **the model**: sentences claiming an employer, skill, responsibility or trait the profile doesn't show. Each
  answer must quote the document exactly; a quote that isn't in it is dropped, so a confused reply can't flag
  words the document never said.

Each warning carries the sentence its words are in. Warnings never block: the person removes the line, says
"It's true" (kept), or says it's wrong and what's true instead; a rewrite then uses those corrections (and they
count as the person's own facts in the check of what it writes).
"""

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from apply.libs.jobs import JobContext
from apply.libs.llm import LLMError
from apply.packs import get_pack
from apply.packs.base import ProfileInput
from apply.runtime import Runtime
from apply.store.sql.repo import applications as applications_repo
from apply.store.sql.repo import documents as documents_repo
from apply.store.sql.repo import opportunities as opportunities_repo
from apply.store.sql.repo import profiles as profiles_repo

logger = logging.getLogger("apply.logic.claims")

MARKER = re.compile(r"\[CONFIRM:[^\]]*\]", re.IGNORECASE)
# A number that claims something: 30%, 12 engineers, $2M, 3x, 5+ years. Dates and contact details are left alone.
# All of a number's digits ("2024" is never read as "202").
NUMBER = re.compile(
    r"(?<![\w./@-])(?:[$€£₹]\s?)?(?:\d{1,3}(?:[,.]\d{3})+|\d+)(?:\.\d+)?(?![\d,.]?\d)"
    r"\s?(?:%|\+|x\b|k\b|m\b|million\b|billion\b)?"
    r"(?:\s?(?:years?|yrs?|months?|people|engineers|users|customers|clients|teams?|projects?|countries))?",
    re.IGNORECASE,
)
YEAR = re.compile(r"^(19|20)\d\d$")
# A date in the profile ("2024-06-30", "2024-06") counts only as its year: its month and day back up no claim.
ISO_DATE = re.compile(r"\b((?:19|20)\d\d)-\d\d(?:-\d\d)?\b")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[(\"“])")
SENTENCE_LIMIT = 400
_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
# A letter's date, as apply writes it ("October 27, 2026") or a person might ("27 October 2026").
DATE_LINE = re.compile(rf"^\s*({_MONTH}\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\s+{_MONTH},?\s+\d{{4}})\s*$", re.IGNORECASE)


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _id(kind: str, quote: str) -> str:
    return hashlib.sha256(f"{kind}:{_plain(quote)}".encode()).hexdigest()[:12]


def _contact_line(line: str) -> bool:
    return "@" in line or "http" in line or bool(re.search(r"\+?\d[\d\s()-]{7,}\d", line))


def rule_warnings(document: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """The deterministic warnings: markers, and numbers the profile doesn't contain."""
    found: list[dict[str, Any]] = []
    for m in MARKER.finditer(document):
        found.append({"kind": "confirm", "quote": m.group(0), "reason": "The writer left this for you to fill in."})
    profile_text = ISO_DATE.sub(r"\1", _plain(json.dumps(profile, ensure_ascii=False)))
    profile_numbers = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(?<=\d),(?=\d{3})", "", profile_text)))
    for line in document.splitlines():
        if _contact_line(line) or DATE_LINE.match(line) or MARKER.search(line):
            continue
        for m in NUMBER.finditer(line):
            quote = m.group(0).strip()
            digits = re.findall(r"\d+(?:\.\d+)?", quote.replace(",", ""))
            if not digits or all(YEAR.match(d) for d in digits):
                continue
            if all(d in profile_numbers for d in digits):
                continue
            found.append({"kind": "number", "quote": quote, "reason": "This number isn't in your profile."})
    return found


def _bare(line: str) -> str:
    """A line as read: no heading marks, bullets, emphasis or link targets."""
    line = re.sub(r"^\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)", "", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    return re.sub(r"\s+", " ", line.replace("**", "").replace("__", "")).strip()


def sentence_of(document: str, quote: str) -> str | None:
    """The sentence (or list line) of the document the quote is in, so a warning can be read in place."""
    wanted = _plain(quote.replace("*", "").replace("_", ""))
    if not wanted:
        return None
    for line in document.splitlines():
        bare = _bare(line)
        if wanted not in _plain(bare.replace("_", "")):
            continue
        for sentence in SENTENCE_END.split(bare):
            if wanted in _plain(sentence.replace("_", "")):
                return sentence if len(sentence) <= SENTENCE_LIMIT else sentence[: SENTENCE_LIMIT - 1] + "…"
        return bare[: SENTENCE_LIMIT - 1] + "…" if len(bare) > SENTENCE_LIMIT else bare
    return None


def with_sentences(document: str, warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**w, "sentence": w.get("sentence") or sentence_of(document, w["quote"])} for w in warnings]


def feedback_facts(revision: dict[str, Any] | None) -> dict[str, Any]:
    """
    What the person told apply while reviewing, as profile facts: their corrections and notes. A rewrite is
    written from them, and its check counts them as backed (they are the person's own word).
    """
    if not revision:
        return {}
    facts: dict[str, Any] = {}
    corrections = [
        {"wrong": c["quote"], "in": c.get("sentence") or "", "true": c.get("correction") or "(take it out)"}
        for c in revision.get("corrections") or []
    ]
    if corrections:
        facts["corrections_from_you"] = corrections
    if (revision.get("notes") or "").strip():
        facts["notes_from_you"] = revision["notes"].strip()
    return facts


def verified(document: str, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The model's claims whose quote really is in the document (ignoring case and spacing)."""
    plain = _plain(document.replace("*", "").replace("_", ""))
    out = []
    for claim in claims:
        quote = str(claim.get("quote", "")).strip().strip('"“”')
        if len(quote) >= 3 and _plain(quote.replace("*", "").replace("_", "")) in plain:
            out.append(
                {
                    "kind": "unsupported",
                    "quote": quote[:300],
                    "reason": str(claim.get("reason", "")).strip()[:300] or "Your profile doesn't say this.",
                }
            )
    return out


def merge(previous: list[dict[str, Any]], fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fresh warnings, de-duplicated, keeping what the person already decided about the same words."""
    decided = {w["id"]: w for w in previous if w.get("resolved")}
    out: dict[str, dict[str, Any]] = {}
    for warning in fresh:
        wid = _id(warning["kind"] if warning["kind"] != "number" else "number", warning["quote"])
        if wid in out:
            continue
        before = decided.get(wid, {})
        out[wid] = {**warning, "id": wid, "resolved": before.get("resolved")}
        if before.get("resolved") == "wrong":
            out[wid]["correction"] = before.get("correction") or ""
    return list(out.values())


async def check(rt: Runtime, ctx: JobContext) -> None:
    """``document.check``: rules, then the model, on a ready document version."""
    document_id = ctx.payload["document_id"]
    async with rt.db.transaction() as session:
        doc = await documents_repo.get_any_owner(session, document_id)
        if doc is None or doc.status != "ready":
            return
        owner_id = doc.owner_id
        application = await applications_repo.get_any_owner(session, doc.application_id)
        if application is None:
            return
        opp = await opportunities_repo.get(session, owner_id, application.opportunity_id)
        pack = get_pack(opp.pack)
        profile = None
        if doc.profile_id:
            try:
                profile = await profiles_repo.get(session, owner_id, doc.profile_id)
            except Exception:  # noqa: BLE001 - deleted since: fall back to the default
                profile = None
        profile = profile or await profiles_repo.default_for(session, owner_id, opp.pack)
        content, previous = doc.content_markdown, list(doc.claim_warnings or [])
        if profile is None:
            doc.claims_status = "skipped"
            return
        attributes = {**profile.attributes, **feedback_facts(doc.revision)}
        person = {"name": profile.name, "summary": profile.summary, **attributes}
        prompt = pack.claims_prompt(
            content, ProfileInput(name=profile.name, summary=profile.summary, attributes=attributes)
        )

    warnings = rule_warnings(content, person)
    status = "checked"
    try:
        data = await rt.model.complete_json(prompt.text, pack.claims_schema, purpose=prompt.purpose)
        warnings += verified(content, list(data.get("claims") or [])[:10])
    except LLMError as exc:
        logger.warning("claims: the model could not check %s: %s", document_id, exc)
        status = "failed"  # the rules' warnings still stand; the model's part can be asked again

    async with rt.db.transaction() as session:
        doc = await documents_repo.get_any_owner(session, document_id, for_update=True)
        if doc is None or doc.content_markdown != content:
            return  # edited meanwhile: that version gets its own check
        doc.claim_warnings = merge(previous, with_sentences(content, warnings))
        doc.claims_status = status
        doc.claims_checked_at = datetime.now(UTC)


async def give_up(rt: Runtime, ctx: JobContext) -> None:
    async with rt.db.transaction() as session:
        doc = await documents_repo.get_any_owner(session, ctx.payload["document_id"], for_update=True)
        if doc is not None and doc.claims_status == "pending":
            doc.claims_status = "failed"
