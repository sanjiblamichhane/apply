"""
apply's portable format, ``apply-export/1``: everything one owner made, as JSON. That means their settings,
profiles, opportunities, applications (with their stage, history and submissions), documents (every finished
version, with its claim warnings and review), saved answers, sources, searches and matches. It is the backup
and the restore.

Left out on purpose: sign-in sessions and API tokens (secrets: make new ones), briefings and PDFs (made again
from the rest), and Auto's runs and screenshots (a run's outcome is kept as its submission). A search's Auto
switch is imported off, and an import never un-pauses Auto: sending is turned on again by hand.

Importing is one transaction: all of it or none. Each item carries a ``ref`` unique within its source; the
``imports`` table remembers what each ref became, so importing the same file again adds only what is new.
Items that don't fit (an unknown pack, attributes the pack refuses) are skipped and reported, never guessed at.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ApplyError
from apply.i18n import Locale
from apply.packs import DEFAULT_PACK, all_packs
from apply.store.sql.models import (
    Answer,
    Application,
    ApplicationDocument,
    DocumentTemplate,
    ImportRef,
    Match,
    Opportunity,
    Pipeline,
    Profile,
    Search,
    Source,
    Stage,
    StageHistory,
    Submission,
    User,
)
from apply.store.sql.repo import packs as packs_repo

from . import templates

logger = logging.getLogger("apply.logic.portable")
FORMAT = "apply-export/1"


class _Item(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ref: str = Field(min_length=1, max_length=200)


class PortableProfile(_Item):
    pack: str = DEFAULT_PACK
    kind: Literal["individual", "organisation"] = "individual"
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)
    tone_instructions: str = ""
    is_default: bool = False


class PortableOpportunity(_Item):
    pack: str = DEFAULT_PACK
    title: str = ""
    issuer_name: str = ""
    source_url: str | None = None
    apply_url: str | None = None
    deadline: datetime | None = None
    status: Literal["open", "closed", "rolling", "draft"] = "open"
    attributes: dict[str, Any] = Field(default_factory=dict)
    external_ref: str | None = None
    source_text: str = ""
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class PortableHistory(BaseModel):
    stage_code: str
    entered_at: datetime
    exited_at: datetime | None = None
    outcome: str = ""
    note: str = ""


class PortableDocument(_Item):
    document_type: str
    version: int = Field(ge=1)
    is_active: bool = False
    content_markdown: str
    source: Literal["generated", "uploaded", "imported", "edited", "rewritten"] = "imported"
    model: str | None = None
    profile_ref: str | None = None
    created_at: datetime | None = None
    claim_warnings: list[dict[str, Any]] = Field(default_factory=list)
    claims_status: str | None = None
    reviewed_at: datetime | None = None
    revision: dict[str, Any] | None = None


class PortableSubmission(_Item):
    channel: Literal["manual", "extension", "auto"] = "manual"
    submitted_at: datetime
    documents: list[Any] = Field(default_factory=list)
    answers: list[Any] = Field(default_factory=list)
    note: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    undone_at: datetime | None = None


class PortableApplication(_Item):
    opportunity_ref: str
    profile_ref: str | None = None
    stage_code: str = "new"
    submitted_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    history: list[PortableHistory] = Field(default_factory=list)
    documents: list[PortableDocument] = Field(default_factory=list)
    submissions: list[PortableSubmission] = Field(default_factory=list)


class PortableSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    locale: Locale = "en"
    time_zone: str = "UTC"
    briefing_hour: int = Field(default=7, ge=0, le=23)
    auto_paused: bool = False
    auto_min_score: int = Field(default=80, ge=0, le=100)
    auto_daily_cap: int = Field(default=5, ge=0, le=100)


class PortableAnswer(_Item):
    pack: str = DEFAULT_PACK
    key: str = Field(min_length=1, max_length=80)
    question: dict[str, str]
    answer: str = ""
    answer_type: str = "text"
    choices: list[Any] = Field(default_factory=list)
    is_sensitive: bool = False
    source: str = "user"
    position: int = 0


class PortableSource(_Item):
    pack: str = DEFAULT_PACK
    kind: str
    name: str = Field(min_length=1, max_length=200)
    config: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    interval_hours: float = 6.0


class PortableSearch(_Item):
    pack: str = DEFAULT_PACK
    name: str = Field(min_length=1, max_length=200)
    criteria: dict[str, Any] = Field(default_factory=dict)
    profile_ref: str | None = None
    min_score: int = 0
    enabled: bool = True
    auto_enabled: bool = False


class PortableMatch(_Item):
    opportunity_ref: str
    search_refs: list[str] = Field(default_factory=list)
    status: Literal["new", "saved", "dismissed", "tracked"] = "new"
    status_changed_at: datetime | None = None
    prefilter: dict[str, Any] = Field(default_factory=dict)
    score: int | None = None
    score_reasons: list[Any] = Field(default_factory=list)
    dealbreakers: list[Any] = Field(default_factory=list)
    score_status: str = "pending"
    scored_at: datetime | None = None
    model: str | None = None
    profile_ref: str | None = None
    application_ref: str | None = None


class PortableTemplate(BaseModel):
    """A person's own document template (libs/render/template.py): checked again before it's kept."""

    model_config = ConfigDict(extra="ignore")
    kind: Literal["sections", "letter"]
    html: str = Field(min_length=1, max_length=256 * 1024)
    filename: str = Field(default="", max_length=200)


class PortableExport(BaseModel):
    format: Literal["apply-export/1"] = FORMAT
    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "apply"
    settings: PortableSettings | None = None
    profiles: list[PortableProfile] = Field(default_factory=list)
    opportunities: list[PortableOpportunity] = Field(default_factory=list)
    applications: list[PortableApplication] = Field(default_factory=list)
    answers: list[PortableAnswer] = Field(default_factory=list)
    sources: list[PortableSource] = Field(default_factory=list)
    searches: list[PortableSearch] = Field(default_factory=list)
    matches: list[PortableMatch] = Field(default_factory=list)
    templates: list[PortableTemplate] = Field(default_factory=list)


KINDS = (
    "profiles",
    "opportunities",
    "applications",
    "documents",
    "submissions",
    "answers",
    "sources",
    "searches",
    "matches",
    "templates",
)


@dataclass
class ImportReport:
    created: dict[str, int] = field(default_factory=lambda: dict.fromkeys(KINDS, 0))
    already: dict[str, int] = field(default_factory=lambda: dict.fromkeys(KINDS, 0))
    problems: list[str] = field(default_factory=list)


# ─── export ──────────────────────────────────────────────────────────────────

# A submission's screenshots stay with Auto's run, which isn't exported: the rest of its record travels.
NOT_PORTABLE_DETAILS = ("screenshots",)


async def _all(session: AsyncSession, model: Any, owner_id: str) -> list[Any]:
    rows = await session.execute(select(model).where(model.owner_id == owner_id).order_by(model.id))
    return list(rows.scalars().all())


async def export(session: AsyncSession, owner_id: str) -> PortableExport:
    profiles = (
        (await session.execute(select(Profile).where(Profile.owner_id == owner_id).order_by(Profile.id)))
        .scalars()
        .all()
    )
    opportunities = (
        (await session.execute(select(Opportunity).where(Opportunity.owner_id == owner_id).order_by(Opportunity.id)))
        .scalars()
        .all()
    )
    applications = (
        (await session.execute(select(Application).where(Application.owner_id == owner_id).order_by(Application.id)))
        .scalars()
        .all()
    )
    stages = {s.id: s.code for s in (await session.execute(select(Stage))).scalars().all()}
    history = (
        (await session.execute(select(StageHistory).where(StageHistory.owner_id == owner_id).order_by(StageHistory.id)))
        .scalars()
        .all()
    )
    documents = (
        (
            await session.execute(
                select(ApplicationDocument)
                .where(ApplicationDocument.owner_id == owner_id, ApplicationDocument.status == "ready")
                .order_by(ApplicationDocument.id)
            )
        )
        .scalars()
        .all()
    )

    user = await session.get(User, owner_id)
    submissions = await _all(session, Submission, owner_id)
    out = PortableExport(
        settings=PortableSettings(
            locale=user.locale,
            time_zone=user.time_zone,
            briefing_hour=user.briefing_hour,
            auto_paused=user.auto_paused,
            auto_min_score=user.auto_min_score,
            auto_daily_cap=user.auto_daily_cap,
        )
        if user
        else None,
        answers=[
            PortableAnswer(
                ref=a.id,
                pack=a.pack,
                key=a.key,
                question=a.question,
                answer=a.answer,
                answer_type=a.answer_type,
                choices=a.choices,
                is_sensitive=a.is_sensitive,
                source=a.source,
                position=a.position,
            )
            for a in await _all(session, Answer, owner_id)
        ],
        templates=[
            PortableTemplate(kind=t.kind, html=t.html, filename=t.filename)  # type: ignore[arg-type]
            for t in await _all(session, DocumentTemplate, owner_id)
        ],
        sources=[
            PortableSource(
                ref=x.id,
                pack=x.pack,
                kind=x.kind,
                name=x.name,
                config=x.config,
                enabled=x.enabled,
                interval_hours=x.interval_hours,
            )
            for x in await _all(session, Source, owner_id)
        ],
        searches=[
            PortableSearch(
                ref=x.id,
                pack=x.pack,
                name=x.name,
                criteria=x.criteria,
                profile_ref=x.profile_id,
                min_score=x.min_score,
                enabled=x.enabled,
                auto_enabled=x.auto_enabled,
            )
            for x in await _all(session, Search, owner_id)
        ],
        matches=[
            PortableMatch(
                ref=m.id,
                opportunity_ref=m.opportunity_id,
                search_refs=[str(i) for i in m.search_ids or []],
                status=m.status,
                status_changed_at=m.status_changed_at,
                prefilter=m.prefilter,
                score=m.score,
                score_reasons=m.score_reasons,
                dealbreakers=m.dealbreakers,
                score_status=m.score_status,
                scored_at=m.scored_at,
                model=m.model,
                profile_ref=m.profile_id,
                application_ref=m.application_id,
            )
            for m in await _all(session, Match, owner_id)
        ],
        profiles=[
            PortableProfile(
                ref=p.id,
                pack=p.pack,
                kind=p.kind,
                name=p.name,
                summary=p.summary,
                attributes=p.attributes,
                tone_instructions=p.tone_instructions,
                is_default=p.is_default,
            )
            for p in profiles
        ],
        opportunities=[
            PortableOpportunity(
                ref=o.id,
                pack=o.pack,
                title=o.title,
                issuer_name=o.issuer_name,
                source_url=o.source_url,
                apply_url=o.apply_url,
                deadline=o.deadline,
                status=o.status,
                attributes=o.attributes,
                external_ref=o.external_ref,
                source_text=o.source_text,
                first_seen_at=o.first_seen_at,
                last_seen_at=o.last_seen_at,
            )
            for o in opportunities
        ],
    )
    for a in applications:
        out.applications.append(
            PortableApplication(
                ref=a.id,
                opportunity_ref=a.opportunity_id,
                profile_ref=a.profile_id,
                stage_code=stages.get(a.stage_id, "new"),
                submitted_at=a.submitted_at,
                notes=a.notes,
                created_at=a.created_at,
                history=[
                    PortableHistory(
                        stage_code=stages.get(h.stage_id, "new"),
                        entered_at=h.entered_at,
                        exited_at=h.exited_at,
                        outcome=h.outcome,
                        note=h.note,
                    )
                    for h in history
                    if h.application_id == a.id
                ],
                documents=[
                    PortableDocument(
                        ref=d.id,
                        document_type=d.document_type,
                        version=d.version,
                        is_active=d.is_active,
                        content_markdown=d.content_markdown,
                        source=d.source,
                        model=d.model,
                        profile_ref=d.profile_id,
                        created_at=d.created_at,
                        claim_warnings=d.claim_warnings,
                        claims_status=d.claims_status,
                        reviewed_at=d.reviewed_at,
                        revision=d.revision,
                    )
                    for d in documents
                    if d.application_id == a.id
                ],
                submissions=[
                    PortableSubmission(
                        ref=x.id,
                        channel=x.channel,
                        submitted_at=x.submitted_at,
                        documents=x.documents,
                        answers=x.answers,
                        note=x.note,
                        details={k: v for k, v in x.details.items() if k not in NOT_PORTABLE_DETAILS},
                        undone_at=x.undone_at,
                    )
                    for x in submissions
                    if x.application_id == a.id
                ],
            )
        )
    return out


# ─── import ──────────────────────────────────────────────────────────────────


async def _own(session: AsyncSession, model: type, owner_id: str, ref: str) -> str | None:
    """An export restored into the account it came from: its refs are that account's own ids."""
    if len(ref) != 26:
        return None
    found = (await session.execute(select(model.id).where(model.id == ref, model.owner_id == owner_id))).first()
    return found[0] if found else None


class _Refs:
    def __init__(self, session: AsyncSession, owner_id: str, source: str):
        self.session, self.owner_id, self.source = session, owner_id, source
        self.known: dict[str, str] = {}

    async def load(self) -> None:
        rows = (
            (
                await self.session.execute(
                    select(ImportRef).where(ImportRef.owner_id == self.owner_id, ImportRef.source == self.source)
                )
            )
            .scalars()
            .all()
        )
        self.known = {r.source_ref: r.target_id for r in rows}

    def get(self, kind: str, ref: str | None) -> str | None:
        return self.known.get(f"{kind}:{ref}") if ref else None

    async def put(self, kind: str, ref: str, target: str, target_id: str) -> None:
        key = f"{kind}:{ref}"
        self.known[key] = target_id
        self.session.add(
            ImportRef(owner_id=self.owner_id, source=self.source, source_ref=key, target=target, target_id=target_id)
        )


async def import_(
    session: AsyncSession, owner_id: str, data: PortableExport, *, source: str | None = None
) -> ImportReport:
    """Import ``data`` for ``owner_id`` inside the caller's transaction."""
    source = source or f"{data.source}-export"
    report = ImportReport()
    refs = _Refs(session, owner_id, source)
    await refs.load()
    packs = all_packs()
    if data.settings is not None:
        await _import_settings(session, owner_id, data.settings)

    for item in data.profiles:
        if refs.get("profile", item.ref):
            report.already["profiles"] += 1
            continue
        if own := await _own(session, Profile, owner_id, item.ref):
            await refs.put("profile", item.ref, "profiles", own)
            report.already["profiles"] += 1
            continue
        pack = packs.get(item.pack)
        if pack is None:
            report.problems.append(f"profile {item.ref}: no pack {item.pack!r}")
            continue
        try:
            attributes = pack.validate_profile(item.attributes)
        except ApplyError as exc:
            report.problems.append(f"profile {item.ref}: {exc.extra.get('errors') or exc.detail}")
            continue
        has_default = (
            await session.execute(
                select(Profile.id).where(
                    Profile.owner_id == owner_id, Profile.pack == item.pack, Profile.is_default.is_(True)
                )
            )
        ).first()
        profile = Profile(
            owner_id=owner_id,
            pack=item.pack,
            kind=item.kind,
            name=item.name[:200],
            summary=item.summary,
            attributes=attributes,
            tone_instructions=item.tone_instructions,
            is_default=item.is_default and not has_default,
        )
        session.add(profile)
        await session.flush()
        await refs.put("profile", item.ref, "profiles", profile.id)
        report.created["profiles"] += 1

    for item in data.opportunities:
        if refs.get("opportunity", item.ref):
            report.already["opportunities"] += 1
            continue
        if own := await _own(session, Opportunity, owner_id, item.ref):
            await refs.put("opportunity", item.ref, "opportunities", own)
            report.already["opportunities"] += 1
            continue
        pack = packs.get(item.pack)
        if pack is None:
            report.problems.append(f"opportunity {item.ref}: no pack {item.pack!r}")
            continue
        try:
            attributes = pack.validate_opportunity(item.attributes)
        except ApplyError as exc:
            report.problems.append(f"opportunity {item.ref}: {exc.extra.get('errors') or exc.detail}")
            continue
        external_ref = (item.external_ref or f"{source}:{item.ref}")[:2100]
        existing = (
            await session.execute(
                select(Opportunity).where(Opportunity.owner_id == owner_id, Opportunity.external_ref == external_ref)
            )
        ).scalar_one_or_none()
        if existing is not None:  # the same posting, pasted here already
            await refs.put("opportunity", item.ref, "opportunities", existing.id)
            report.already["opportunities"] += 1
            continue
        opportunity = Opportunity(
            owner_id=owner_id,
            pack=item.pack,
            title=item.title[:500],
            issuer_name=item.issuer_name[:300],
            source_url=item.source_url,
            apply_url=item.apply_url,
            deadline=item.deadline,
            status=item.status,
            attributes=attributes,
            external_ref=external_ref,
            content_hash=hashlib.sha256((item.source_text or external_ref).encode()).hexdigest(),
            source_text=item.source_text,
            extraction={"status": "ready", "method": "import", "error_code": None},
            **({"first_seen_at": item.first_seen_at} if item.first_seen_at else {}),
            **({"last_seen_at": item.last_seen_at} if item.last_seen_at else {}),
        )
        session.add(opportunity)
        await session.flush()
        await refs.put("opportunity", item.ref, "opportunities", opportunity.id)
        report.created["opportunities"] += 1

    await _import_sources(session, owner_id, data.sources, refs, report)
    await _import_searches(session, owner_id, data.searches, refs, report)

    pipelines: dict[str, tuple[Pipeline, dict[str, Stage]]] = {}
    for item in data.applications:
        application_id = refs.get("application", item.ref)
        opportunity_id = refs.get("opportunity", item.opportunity_ref)
        if opportunity_id is None:
            report.problems.append(f"application {item.ref}: its opportunity {item.opportunity_ref} wasn't imported")
            continue
        opportunity = await session.get(Opportunity, opportunity_id)
        assert opportunity is not None
        if opportunity.pack not in pipelines:
            pipeline = await packs_repo.default_pipeline(session, opportunity.pack, owner_id)
            if pipeline is None:
                report.problems.append(f"application {item.ref}: the {opportunity.pack} pack has no pipeline")
                continue
            stages = {s.code: s for s in await packs_repo.stages_of(session, pipeline.id)}
            pipelines[opportunity.pack] = (pipeline, stages)
        pipeline, stages = pipelines[opportunity.pack]
        first = min(stages.values(), key=lambda s: s.position)

        def stage_for(code: str, stages: dict[str, Stage] = stages, first: Stage = first) -> Stage:
            return stages.get(code) or first

        if application_id is None:
            existing = (
                await session.execute(
                    select(Application).where(
                        Application.owner_id == owner_id, Application.opportunity_id == opportunity_id
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                application_id = existing.id
                report.already["applications"] += 1
            else:
                application = Application(
                    owner_id=owner_id,
                    opportunity_id=opportunity_id,
                    profile_id=refs.get("profile", item.profile_ref),
                    pipeline_id=pipeline.id,
                    stage_id=stage_for(item.stage_code).id,
                    submitted_at=item.submitted_at,
                    notes=item.notes,
                    **({"created_at": item.created_at} if item.created_at else {}),
                )
                session.add(application)
                await session.flush()
                application_id = application.id
                history = item.history or [
                    PortableHistory(stage_code=item.stage_code, entered_at=item.created_at or datetime.now(UTC))
                ]
                for entry in sorted(history, key=lambda h: h.entered_at):
                    session.add(
                        StageHistory(
                            owner_id=owner_id,
                            application_id=application_id,
                            stage_id=stage_for(entry.stage_code).id,
                            entered_at=entry.entered_at,
                            exited_at=entry.exited_at,
                            outcome=entry.outcome[:20],
                            note=entry.note,
                        )
                    )
                report.created["applications"] += 1
            await refs.put("application", item.ref, "applications", application_id)
        else:
            report.already["applications"] += 1

        await _import_documents(session, owner_id, application_id, item, refs, report)
        await _import_submissions(session, owner_id, application_id, item, refs, report)

    await _import_matches(session, owner_id, data.matches, refs, report)
    await _import_answers(session, owner_id, data.answers, refs, report)
    await _import_templates(session, owner_id, data.templates, report)
    await session.flush()
    return report


async def _import_templates(
    session: AsyncSession, owner_id: str, items: list[PortableTemplate], report: ImportReport
) -> None:
    """A template comes in only if it passes today's checks, and never over one the person has here already."""
    for item in items:
        if await templates.mine(session, owner_id, item.kind) is not None:
            report.already["templates"] += 1
            continue
        if templates.check(item.html, item.kind):
            report.problems.append(f"The {item.kind} template didn't pass the checks, so the default is used.")
            continue
        session.add(DocumentTemplate(owner_id=owner_id, kind=item.kind, html=item.html, filename=item.filename))
        report.created["templates"] += 1


async def _import_documents(
    session: AsyncSession,
    owner_id: str,
    application_id: str,
    item: PortableApplication,
    refs: _Refs,
    report: ImportReport,
) -> None:
    for kind in sorted({d.document_type for d in item.documents}):
        docs = sorted((d for d in item.documents if d.document_type == kind), key=lambda d: d.version)
        current = (
            (
                await session.execute(
                    select(ApplicationDocument).where(
                        ApplicationDocument.application_id == application_id, ApplicationDocument.document_type == kind
                    )
                )
            )
            .scalars()
            .all()
        )
        last = max((d.version for d in current), default=0)
        has_active = any(d.is_active for d in current)
        for doc in docs:
            if refs.get("document", doc.ref):
                report.already["documents"] += 1
                continue
            if own := await _own(session, ApplicationDocument, owner_id, doc.ref):
                await refs.put("document", doc.ref, "application_documents", own)
                report.already["documents"] += 1
                continue
            last += 1
            active = doc.is_active and not has_active
            has_active = has_active or active
            row = ApplicationDocument(
                owner_id=owner_id,
                application_id=application_id,
                profile_id=refs.get("profile", doc.profile_ref),
                document_type=kind,
                status="ready",
                version=last,
                is_active=active,
                content_markdown=doc.content_markdown,
                source="imported",
                model=doc.model,
                claim_warnings=doc.claim_warnings,
                # Checked where it came from, or checked again here (an import from elsewhere wasn't).
                claims_status=doc.claims_status if doc.claims_status in ("checked", "failed", "skipped") else "pending",
                reviewed_at=doc.reviewed_at,
                revision=doc.revision,
                finished_at=doc.created_at or datetime.now(UTC),
                **({"created_at": doc.created_at} if doc.created_at else {}),
            )
            session.add(row)
            await session.flush()
            await refs.put("document", doc.ref, "application_documents", row.id)
            report.created["documents"] += 1


async def _import_settings(session: AsyncSession, owner_id: str, settings: PortableSettings) -> None:
    user = await session.get(User, owner_id)
    if user is None:
        return
    user.locale, user.time_zone, user.briefing_hour = settings.locale, settings.time_zone, settings.briefing_hour
    user.auto_min_score, user.auto_daily_cap = settings.auto_min_score, settings.auto_daily_cap
    user.auto_paused = user.auto_paused or settings.auto_paused  # an import may pause Auto, never un-pause it


async def _import_sources(
    session: AsyncSession, owner_id: str, items: list[PortableSource], refs: _Refs, report: ImportReport
) -> None:
    packs = all_packs()
    for item in items:
        if refs.get("source", item.ref):
            report.already["sources"] += 1
            continue
        if own := await _own(session, Source, owner_id, item.ref):
            await refs.put("source", item.ref, "sources", own)
            report.already["sources"] += 1
            continue
        pack = packs.get(item.pack)
        try:
            if pack is None:
                raise LookupError(f"no pack {item.pack!r}")
            adapter = pack.source(item.kind)
            config = adapter.validate_config(item.config)
        except (ApplyError, LookupError, KeyError) as exc:
            report.problems.append(f"source {item.ref}: {getattr(exc, 'detail', None) or exc}")
            continue
        same = (
            await session.execute(
                select(Source).where(Source.owner_id == owner_id, Source.pack == item.pack, Source.kind == item.kind)
            )
        ).scalars()
        existing = next((x for x in same if x.config == config), None)
        if existing is not None:
            await refs.put("source", item.ref, "sources", existing.id)
            report.already["sources"] += 1
            continue
        source = Source(
            owner_id=owner_id,
            pack=item.pack,
            kind=item.kind,
            name=item.name[:200],
            config=config,
            enabled=item.enabled,
            interval_hours=max(item.interval_hours, adapter.min_interval_hours),
        )
        session.add(source)
        await session.flush()
        await refs.put("source", item.ref, "sources", source.id)
        report.created["sources"] += 1


async def _import_searches(
    session: AsyncSession, owner_id: str, items: list[PortableSearch], refs: _Refs, report: ImportReport
) -> None:
    packs = all_packs()
    for item in items:
        if refs.get("search", item.ref):
            report.already["searches"] += 1
            continue
        if own := await _own(session, Search, owner_id, item.ref):
            await refs.put("search", item.ref, "searches", own)
            report.already["searches"] += 1
            continue
        if item.pack not in packs:
            report.problems.append(f"search {item.ref}: no pack {item.pack!r}")
            continue
        criteria = dict(item.criteria)
        criteria["source_ids"] = [
            target for ref in criteria.get("source_ids") or [] if (target := refs.get("source", str(ref)))
        ]
        search = Search(
            owner_id=owner_id,
            pack=item.pack,
            name=item.name[:200],
            criteria=criteria,
            profile_id=refs.get("profile", item.profile_ref),
            min_score=item.min_score,
            enabled=item.enabled,
            auto_enabled=False,  # Auto is turned on again by hand, on this copy
        )
        session.add(search)
        await session.flush()
        await refs.put("search", item.ref, "searches", search.id)
        report.created["searches"] += 1


async def _import_submissions(
    session: AsyncSession,
    owner_id: str,
    application_id: str,
    item: PortableApplication,
    refs: _Refs,
    report: ImportReport,
) -> None:
    for sub in item.submissions:
        if refs.get("submission", sub.ref):
            report.already["submissions"] += 1
            continue
        if own := await _own(session, Submission, owner_id, sub.ref):
            await refs.put("submission", sub.ref, "submissions", own)
            report.already["submissions"] += 1
            continue
        row = Submission(
            owner_id=owner_id,
            application_id=application_id,
            channel=sub.channel,
            submitted_at=sub.submitted_at,
            documents=sub.documents,
            answers=sub.answers,
            note=sub.note,
            details=sub.details,
            undone_at=sub.undone_at,
        )
        session.add(row)
        await session.flush()
        await refs.put("submission", sub.ref, "submissions", row.id)
        report.created["submissions"] += 1


async def _import_matches(
    session: AsyncSession, owner_id: str, items: list[PortableMatch], refs: _Refs, report: ImportReport
) -> None:
    for item in items:
        opportunity_id = refs.get("opportunity", item.opportunity_ref)
        if opportunity_id is None:
            report.problems.append(f"match {item.ref}: its opportunity {item.opportunity_ref} wasn't imported")
            continue
        if refs.get("match", item.ref):
            report.already["matches"] += 1
            continue
        existing = (
            await session.execute(
                select(Match.id).where(Match.owner_id == owner_id, Match.opportunity_id == opportunity_id)
            )
        ).first()
        if existing is not None:
            await refs.put("match", item.ref, "matches", existing[0])
            report.already["matches"] += 1
            continue
        match = Match(
            owner_id=owner_id,
            opportunity_id=opportunity_id,
            search_ids=[target for ref in item.search_refs if (target := refs.get("search", ref))],
            status=item.status,
            status_changed_at=item.status_changed_at,
            prefilter=item.prefilter,
            score=item.score,
            score_reasons=item.score_reasons,
            dealbreakers=item.dealbreakers,
            score_status=item.score_status,
            scored_at=item.scored_at,
            model=item.model,
            profile_id=refs.get("profile", item.profile_ref),
            application_id=refs.get("application", item.application_ref),
        )
        session.add(match)
        await session.flush()
        await refs.put("match", item.ref, "matches", match.id)
        report.created["matches"] += 1


async def _import_answers(
    session: AsyncSession, owner_id: str, items: list[PortableAnswer], refs: _Refs, report: ImportReport
) -> None:
    packs = all_packs()
    for item in items:
        if item.pack not in packs:
            report.problems.append(f"answer {item.ref}: no pack {item.pack!r}")
            continue
        existing = (
            await session.execute(
                select(Answer).where(Answer.owner_id == owner_id, Answer.pack == item.pack, Answer.key == item.key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            if not existing.answer and item.answer:  # a default never answered here: take the exported answer
                existing.answer = item.answer
            report.already["answers"] += 1
            continue
        answer = Answer(
            owner_id=owner_id,
            pack=item.pack,
            key=item.key,
            question=item.question,
            answer=item.answer,
            answer_type=item.answer_type,
            choices=item.choices,
            is_sensitive=item.is_sensitive,
            source=item.source,
            position=item.position,
        )
        session.add(answer)
        await session.flush()
        await refs.put("answer", item.ref, "answers", answer.id)
        report.created["answers"] += 1
