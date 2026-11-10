"""
apply's tables.

Every row someone owns carries ``owner_id``, and every query filters on it (store/sql/repo), even while there is
one owner: a hosted, multi-user apply must not need a security rewrite. Rows that come with apply itself (the
packs, their default pipelines and stages) have ``owner_id`` NULL and are read-only through the API.

Ids are ULIDs (sortable by creation time, so they double as page cursors). Labels a person sees are JSON
``{"en": …, "ne": …}``.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from apply.libs.jobs import jobs_table

from .db import new_id

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}


class Row:
    # Server-made values (created_at, updated_at) come back with the INSERT or UPDATE (RETURNING), so nothing is
    # loaded lazily later, which async sessions can't do.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def owner_column(*, system: bool = False) -> Mapped[str | None]:
    return mapped_column(String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=system, index=True)


# ─── accounts ────────────────────────────────────────────────────────────────


class User(Row, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(5), default="en", server_default="en")
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    failed_sign_ins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sign_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Turned off by the owner: no sign-in, its sessions and tokens stop working; its data stays.
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_zone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")  # IANA name
    briefing_hour: Mapped[int] = mapped_column(Integer, default=7, server_default="7")  # in time_zone
    # Auto: one switch pauses all of it; the rest are its limits.
    auto_paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    auto_min_score: Mapped[int] = mapped_column(Integer, default=80, server_default="80")
    auto_daily_cap: Mapped[int] = mapped_column(Integer, default=5, server_default="5")


class Session(Row, Base):
    __tablename__ = "sessions"

    owner_id: Mapped[str] = owner_column()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 hex; the token is only in the cookie
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agent: Mapped[str] = mapped_column(String(300), default="", server_default="")


class KnownDevice(Row, Base):
    """
    A browser this account has signed in from. A lock after failed sign-ins (someone guessing) doesn't apply to
    it, so a stranger can't lock the owner out. Only the cookie's SHA-256 is kept.
    """

    __tablename__ = "known_devices"

    owner_id: Mapped[str] = owner_column()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordReset(Row, Base):
    """
    A "Forgot your password?" link: works once, until expires_at. Only the token's SHA-256 is kept; the token
    itself is only in the email.
    """

    __tablename__ = "password_resets"

    owner_id: Mapped[str] = owner_column()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InstallSettings(Row, Base):
    """
    This install's own settings, the owner's to change (one row, id "current"; none: the defaults). Not a
    person's: no owner, not exported.
    """

    __tablename__ = "install_settings"

    # Anyone may create an account on the sign-in page (the first one is always the owner's).
    registration_open: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class ModelChoiceRow(Row, Base):
    """
    The model this install uses, as chosen in Settings → Model (one row, id "current"; none: the settings'). The
    machine's, not a person's: it has no owner and isn't exported. Only written after the model passed a test.
    """

    __tablename__ = "model_choice"

    api: Mapped[str] = mapped_column(String(16))  # "native" (/api/chat) or "v1" (/v1/chat/completions)
    base_url: Mapped[str] = mapped_column(String(300))
    model: Mapped[str] = mapped_column(String(300))
    writing_model: Mapped[str] = mapped_column(String(300), default="", server_default="")
    num_ctx: Mapped[int] = mapped_column(Integer)


class ApiToken(Row, Base):
    """
    A personal API token for the extension (later the runner): scoped, revocable, optionally expiring. Only the
    secret's SHA-256 is kept; ``prefix`` is its first characters, so a person can tell tokens apart.
    """

    __tablename__ = "api_tokens"

    owner_id: Mapped[str] = owner_column()
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(12), default="extension", server_default="extension")
    prefix: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ─── packs and pipelines ─────────────────────────────────────────────────────


class Pack(Row, Base):
    __tablename__ = "packs"

    owner_id: Mapped[str | None] = owner_column(system=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    version: Mapped[str] = mapped_column(String(20))
    label: Mapped[dict[str, Any]] = mapped_column(JSONB)
    description: Mapped[dict[str, Any]] = mapped_column(JSONB)
    profile_schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    opportunity_schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    document_types: Mapped[list[Any]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Pipeline(Row, Base):
    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("owner_id", "pack", "key", postgresql_nulls_not_distinct=True),)

    owner_id: Mapped[str | None] = owner_column(system=True)
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(60))
    label: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class Stage(Row, Base):
    __tablename__ = "stages"
    __table_args__ = (UniqueConstraint("pipeline_id", "code"),)

    owner_id: Mapped[str | None] = owner_column(system=True)
    pipeline_id: Mapped[str] = mapped_column(String(26), ForeignKey("pipelines.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(60))
    label: Mapped[dict[str, Any]] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20))  # pre_pipeline | active | success | failure | paused
    action_type: Mapped[str] = mapped_column(String(20))
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    follow_up_after_days: Mapped[int | None] = mapped_column(Integer)
    expected_duration_days: Mapped[int | None] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


# ─── who applies, and to what ────────────────────────────────────────────────


class Profile(Row, Base):
    __tablename__ = "profiles"
    __table_args__ = (
        Index("uq_profiles_one_default", "owner_id", "pack", unique=True, postgresql_where=text("is_default")),
    )

    owner_id: Mapped[str] = owner_column()
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key"))
    kind: Mapped[str] = mapped_column(String(20))  # individual | organisation
    name: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    tone_instructions: Mapped[str] = mapped_column(Text, default="", server_default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    # Made from an uploaded document (a resume): the file (in the bucket: {key, name, kind, size}), its text, and
    # the model's reading of it ({status: pending | ready | failed | stopped, error_code}). {} when typed in.
    source: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    source_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    reading: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))


class Opportunity(Row, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("owner_id", "external_ref"),
        Index("ix_opportunities_dedupe", "owner_id", "dedupe_key"),
    )

    owner_id: Mapped[str] = owner_column()
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key"))
    title: Mapped[str] = mapped_column(String(500), default="", server_default="")
    issuer_name: Mapped[str] = mapped_column(String(300), default="", server_default="")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    apply_url: Mapped[str | None] = mapped_column(String(2048))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), default="open", server_default="open")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    external_ref: Mapped[str] = mapped_column(String(2100))  # the canonical URL, or text:<sha256>
    content_hash: Mapped[str] = mapped_column(String(64))
    source_text: Mapped[str] = mapped_column(Text, default="", server_default="")  # what was pasted or read
    extraction: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    # Discovery: which source listed it, the key that makes it the same job on another source, when it was posted.
    source_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("sources.id", ondelete="SET NULL"))
    dedupe_key: Mapped[str | None] = mapped_column(String(500))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Application(Row, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("owner_id", "opportunity_id"),
        Index("ix_applications_stage", "owner_id", "stage_id"),
    )

    owner_id: Mapped[str] = owner_column()
    opportunity_id: Mapped[str] = mapped_column(String(26), ForeignKey("opportunities.id", ondelete="CASCADE"))
    profile_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("profiles.id", ondelete="SET NULL"))
    pipeline_id: Mapped[str] = mapped_column(String(26), ForeignKey("pipelines.id"))
    stage_id: Mapped[str] = mapped_column(String(26), ForeignKey("stages.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    analysis: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    # Loaded on purpose (repo.applications), never by accident: lazy="raise".
    opportunity: Mapped[Opportunity] = relationship(lazy="raise", viewonly=True)
    stage: Mapped[Stage] = relationship(lazy="raise", viewonly=True)
    # The documents in use or being written: what a card shows ("Resume ready, cover letter being written").
    current_documents: Mapped[list["ApplicationDocument"]] = relationship(
        lazy="raise",
        viewonly=True,
        primaryjoin="and_(Application.id == foreign(ApplicationDocument.application_id), "
        "or_(ApplicationDocument.is_active, ApplicationDocument.status != 'ready'))",
        order_by="ApplicationDocument.id.desc()",
    )


class StageHistory(Row, Base):
    __tablename__ = "stage_history"

    owner_id: Mapped[str] = owner_column()
    application_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[str] = mapped_column(String(26), ForeignKey("stages.id"))
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(20), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")

    stage: Mapped[Stage] = relationship(lazy="raise", viewonly=True)


class ApplicationDocument(Row, Base):
    """
    A document written (or uploaded) for one application. One written in the background exists from the moment
    it is asked for, so the request returns at once; until it is ready it is inactive with version 0, so the
    versions people see are only ever finished ones and the one in use stays in use.
    """

    __tablename__ = "application_documents"
    __table_args__ = (
        Index("ix_application_documents_app", "application_id", "document_type"),
        Index(
            "uq_application_documents_active",
            "application_id",
            "document_type",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "uq_application_documents_pending",
            "application_id",
            "document_type",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "uq_application_documents_version",
            "application_id",
            "document_type",
            "version",
            unique=True,
            postgresql_where=text("version > 0"),
        ),
    )

    owner_id: Mapped[str] = owner_column()
    application_id: Mapped[str] = mapped_column(String(26), ForeignKey("applications.id", ondelete="CASCADE"))
    profile_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("profiles.id", ondelete="SET NULL"))
    document_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    error_code: Mapped[str | None] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    content_markdown: Mapped[str] = mapped_column(Text, default="", server_default="")
    claim_warnings: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    source: Mapped[str] = mapped_column(String(20), default="generated", server_default="generated")
    model: Mapped[str | None] = mapped_column(String(100))
    generation_ms: Mapped[int | None] = mapped_column(Integer)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Review: the claim check's state, and when the person said they'd read this version.
    claims_status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending")
    claims_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A rewrite's brief: the version it comes from, the person's notes and corrections (kept, so later rewrites
    # and the check of what was written know them).
    revision: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


# ─── discovery ───────────────────────────────────────────────────────────────


class Source(Row, Base):
    """A public listings API to fetch from (a company's job board, a public tender feed)."""

    __tablename__ = "sources"

    owner_id: Mapped[str] = owner_column()
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key"))
    kind: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    interval_hours: Mapped[float] = mapped_column(Float, default=6.0, server_default="6")
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(12), default="never", server_default="never")  # ok | failed
    last_error_code: Mapped[str | None] = mapped_column(String(60))
    last_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Search(Row, Base):
    """Saved criteria: which postings are worth a look, and whose profile to score them against."""

    __tablename__ = "searches"

    owner_id: Mapped[str] = owner_column()
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key"))
    name: Mapped[str] = mapped_column(String(200))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    profile_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("profiles.id", ondelete="SET NULL"))
    min_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    auto_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class Match(Row, Base):
    """An opportunity worth a look, once per owner, however many searches found it."""

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("owner_id", "opportunity_id"),
        Index("ix_matches_inbox", "owner_id", "status", "score", "id"),
    )

    owner_id: Mapped[str] = owner_column()
    opportunity_id: Mapped[str] = mapped_column(String(26), ForeignKey("opportunities.id", ondelete="CASCADE"))
    search_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    status: Mapped[str] = mapped_column(String(12), default="new", server_default="new")
    prefilter: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    score: Mapped[int | None] = mapped_column(Integer)
    score_reasons: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    dealbreakers: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    score_status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    score_error_code: Mapped[str | None] = mapped_column(String(60))
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model: Mapped[str | None] = mapped_column(String(100))
    profile_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("profiles.id", ondelete="SET NULL"))
    application_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("applications.id", ondelete="SET NULL"))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    opportunity: Mapped[Opportunity] = relationship(lazy="raise", viewonly=True)


class Briefing(Row, Base):
    """What's new today: matches, follow-ups due, deadlines. One per owner per day."""

    __tablename__ = "briefings"
    __table_args__ = (UniqueConstraint("owner_id", "date"),)

    owner_id: Mapped[str] = owner_column()
    date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD in the owner's time zone
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ─── review and the Application kit ──────────────────────────────────────────


class RenderedFile(Row, Base):
    """A document version as a file (its page, its PDF), in the bucket at ``object_key``."""

    __tablename__ = "rendered_files"
    __table_args__ = (UniqueConstraint("document_id", "kind", "sha256"),)

    owner_id: Mapped[str] = owner_column()
    document_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("application_documents.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))  # pdf, html, docx
    sha256: Mapped[str] = mapped_column(String(64))  # of what it was made from: the words and the template
    size: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str | None] = mapped_column(String(300))
    data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)  # before 0009; moved to the bucket on start


class DocumentTemplate(Row, Base):
    """
    A person's own template for their resumes or their letters (libs/render/template.py), in place of the
    default; kept only once it passes libs/render/checks.py.
    """

    __tablename__ = "document_templates"
    __table_args__ = (UniqueConstraint("owner_id", "kind"),)

    owner_id: Mapped[str] = owner_column()
    kind: Mapped[str] = mapped_column(String(10))  # resume, letter
    html: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(200), default="")


class Answer(Row, Base):
    """A reusable answer to an application form's question. Sensitive ones are never sent to a model."""

    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("owner_id", "pack", "key"),)

    owner_id: Mapped[str] = owner_column()
    pack: Mapped[str] = mapped_column(String(40), ForeignKey("packs.key"))
    key: Mapped[str] = mapped_column(String(80))
    question: Mapped[dict[str, Any]] = mapped_column(JSONB)  # {"en": …, "ne": …}
    answer: Mapped[str] = mapped_column(Text, default="", server_default="")
    answer_type: Mapped[str] = mapped_column(String(10), default="text", server_default="text")
    choices: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    source: Mapped[str] = mapped_column(String(10), default="user", server_default="user")  # user | learned | pack
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Submission(Row, Base):
    """What was sent, how and when: the record of an application going out."""

    __tablename__ = "submissions"

    owner_id: Mapped[str] = owner_column()
    application_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(12))  # manual | extension | auto
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    documents: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    answers: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    previous_stage_id: Mapped[str | None] = mapped_column(String(26))
    # How it went out: the confirmation page, what the extension filled and what it left for the person.
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ─── Auto ────────────────────────────────────────────────────────────────────


class AutoRun(Row, Base):
    """
    Auto preparing a match for the person to send (logic/auto.py): its state and why it stopped if it did.
    dry_run, drafts and send are what a runner recorded on runs from before apply stopped sending.
    """

    __tablename__ = "auto_runs"
    __table_args__ = (
        UniqueConstraint("owner_id", "match_id"),
        Index("ix_auto_runs_status", "owner_id", "status"),
    )

    owner_id: Mapped[str] = owner_column()
    match_id: Mapped[str] = mapped_column(String(26), ForeignKey("matches.id", ondelete="CASCADE"))
    application_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("applications.id", ondelete="SET NULL"))
    search_id: Mapped[str | None] = mapped_column(String(26), ForeignKey("searches.id", ondelete="SET NULL"))
    # starting | writing | ready | sent | needs_you | stopped | dismissed
    status: Mapped[str] = mapped_column(String(12), default="starting", server_default="starting")
    reason: Mapped[str | None] = mapped_column(String(60))
    reason_detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # prepared: the person's to send
    dry_run: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    drafts: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    send: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    submission_id: Mapped[str | None] = mapped_column(String(26))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    match: Mapped[Match] = relationship(lazy="raise", viewonly=True)


class AutoScreenshot(Row, Base):
    """What a runner's browser showed at a step, on runs from before apply stopped sending (kept as history)."""

    __tablename__ = "auto_screenshots"

    owner_id: Mapped[str] = owner_column()
    run_id: Mapped[str] = mapped_column(String(26), ForeignKey("auto_runs.id", ondelete="CASCADE"), index=True)
    step: Mapped[str] = mapped_column(String(20))
    size: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str | None] = mapped_column(String(300))
    data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)  # before 0009; moved to the bucket on start


# ─── imports ─────────────────────────────────────────────────────────────────


class ImportRef(Row, Base):
    """What an import made from what: a second run of the same import adds only what is new."""

    __tablename__ = "imports"
    __table_args__ = (UniqueConstraint("owner_id", "source", "source_ref"),)

    owner_id: Mapped[str] = owner_column()
    source: Mapped[str] = mapped_column(String(40))  # apply-export, or apply-demo
    source_ref: Mapped[str] = mapped_column(String(200))  # e.g. "application:123"
    target: Mapped[str] = mapped_column(String(40))  # the table
    target_id: Mapped[str] = mapped_column(String(26))


# ─── background work ─────────────────────────────────────────────────────────

jobs = jobs_table(Base.metadata)

# Tables with no owner: accounts themselves, the queue (its jobs carry an optional owner_id), and the install's
# model and settings.
UNOWNED = {"users", "jobs", "model_choice", "install_settings"}
