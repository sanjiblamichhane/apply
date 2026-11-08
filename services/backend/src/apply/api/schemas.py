"""
The API on the wire: what comes in, what goes out, and the one error shape. The OpenAPI schema made from these
is the source of truth for the web app's typed client (services/backend/openapi.json).
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from apply.errors import ErrorCode
from apply.i18n import Locale
from apply.packs import DEFAULT_PACK

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text = Annotated[str, StringConstraints(max_length=20_000)]
Key = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,59}$")]
Id = Annotated[str, StringConstraints(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]
Limit = Annotated[int, Field(ge=1, le=200)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Label(BaseModel):
    """One string in each of apply's languages. A label stored before Spanish was added (a saved answer's question,
    say) has only English and Nepali, and a Spanish reader sees the English."""

    en: str
    ne: str
    es: str | None = None


# ─── errors ──────────────────────────────────────────────────────────────────


class FieldError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class Problem(BaseModel):
    """RFC 9457 Problem Details, with a stable ``code`` the web app translates. ``detail`` is for logs."""

    type: str
    status: int
    title: str
    detail: str
    code: ErrorCode
    errors: list[FieldError] | None = None
    application_id: str | None = None
    retry_after: int | None = None  # seconds, with SIGN_IN_LOCKED (also the Retry-After header)


# ─── system ──────────────────────────────────────────────────────────────────


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    storage: bool  # the file bucket
    version: str


class ModelStatus(BaseModel):
    reachable: bool
    ready: bool
    base_url: str
    version: str | None
    wanted: list[str]
    installed: list[str]
    missing: list[str]
    num_ctx: int | None


class FoundModelOut(BaseModel):
    name: str
    size_bytes: int | None
    parameters: str | None = Field(description='As the server says it: "8.2B"')
    family: str | None
    quantization: str | None
    context_length: int | None
    loaded: bool = Field(description="In memory now: answers without loading first")
    usable: bool = Field(description="Writes text; an embedding model can't be chosen")
    note: Literal["embedding"] | None


class EndpointOut(BaseModel):
    api: Literal["native", "v1"] = Field(description="native: /api/chat and /api/tags; v1: /v1/chat/completions")
    base_url: str
    version: str | None
    models: list[FoundModelOut]


class ModelInUse(BaseModel):
    api: Literal["native", "v1"]
    base_url: str
    model: str
    writing_model: str
    num_ctx: int | None = Field(description="The context size sent (native API); None where the server sets its own")
    source: Literal["chosen", "settings"] = Field(description="Chosen in Settings → Model, or the settings (.env)")


class Models(BaseModel):
    current: ModelInUse
    endpoints: list[EndpointOut]


class ChooseModel(In):
    base_url: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    model: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    writing_model: Annotated[str, StringConstraints(max_length=300)] = ""
    num_ctx: Annotated[int, Field(ge=2048, le=262144)] | None = None


class ModelChosen(BaseModel):
    current: ModelInUse
    milliseconds: int = Field(description="How long the test took (the first use loads the model)")


# ─── accounts ────────────────────────────────────────────────────────────────


class SignIn(In):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class Register(In):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    locale: Locale = "en"
    demo: bool = Field(default=False, description="Add the demo (John Doe, a fictional profile) to look around")


class Setup(BaseModel):
    """Whether "Create an account" is offered, and whether it's the first run (the owner's account)."""

    open: bool
    first_run: bool
    mail: bool = False  # whether "Forgot your password?" can email a link (an SMTP server is set)


class ForgotPassword(In):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]


class ResetToken(In):
    token: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class ResetFor(BaseModel):
    """The account a reset link is for (shown, and given to a password manager)."""

    email: str


class ResetPassword(In):
    token: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class Registration(BaseModel):
    """Whether anyone may create an account on this apply (the owner's switch)."""

    open: bool


class PersonOut(ApiModel):
    """An account, as the owner sees it: never anything in it."""

    id: str
    email: str
    is_owner: bool
    created_at: datetime
    last_sign_in_at: datetime | None
    disabled_at: datetime | None


class People(BaseModel):
    items: list[PersonOut]


class Me(ApiModel):
    id: str
    email: str
    locale: Locale
    is_owner: bool
    time_zone: str
    briefing_hour: int


class MeChanges(In):
    locale: Locale | None = None
    time_zone: (
        Annotated[str, StringConstraints(pattern=r"^[A-Za-z_]+(/[A-Za-z0-9_+-]+){0,2}$", max_length=64)] | None
    ) = None
    briefing_hour: Annotated[int, Field(ge=0, le=23)] | None = None


# ─── packs ───────────────────────────────────────────────────────────────────


class StageOut(ApiModel):
    id: str
    code: str
    label: Label
    position: int
    category: Literal["pre_pipeline", "active", "success", "failure", "paused"]
    action_type: str
    is_terminal: bool
    follow_up_after_days: int | None
    expected_duration_days: int | None
    is_archived: bool


class PipelineOut(ApiModel):
    id: str
    key: str
    label: Label
    stages: list[StageOut]


class DocumentTypeOut(BaseModel):
    key: str
    label: Label
    description: Label
    generatable: bool
    accepts_upload: bool
    layout: Literal["sections", "letter"]  # which of the person's templates it's made in


class PackOut(BaseModel):
    key: str
    version: str
    label: Label
    description: Label
    profile_kinds: list[Literal["individual", "organisation"]]
    search_options: list[Literal["locations", "remote_only", "needs_sponsorship"]]
    auto: bool  # whether Auto can send this pack's applications (it has boards it knows)
    profile_schema: dict[str, Any]
    opportunity_schema: dict[str, Any]
    document_types: list[DocumentTypeOut]
    pipeline: PipelineOut
    category_labels: dict[str, Label]
    action_labels: dict[str, Label]
    profile_kind_labels: dict[str, Label]


class Packs(BaseModel):
    items: list[PackOut]


# ─── profiles ────────────────────────────────────────────────────────────────


class NewProfile(In):
    pack: Key = DEFAULT_PACK
    kind: Literal["individual", "organisation"] = "individual"
    name: Name
    summary: Text = ""
    attributes: dict[str, Any] = Field(default_factory=dict)
    tone_instructions: Annotated[str, StringConstraints(max_length=2000)] = ""
    is_default: bool | None = None


class ProfileChanges(In):
    name: Name | None = None
    summary: Text | None = None
    attributes: dict[str, Any] | None = None
    tone_instructions: Annotated[str, StringConstraints(max_length=2000)] | None = None
    is_default: bool | None = None


class ProfileSource(BaseModel):
    """The document a profile was made from (download it at /profiles/{id}/source)."""

    name: str
    kind: Literal["pdf", "docx", "text"]
    size: int


class ProfileReading(BaseModel):
    """The model reading the document into the fields: pending, ready, failed (error_code says why), or stopped
    (the person edited the profile first, and their edits win)."""

    status: Literal["pending", "ready", "failed", "stopped"]
    error_code: ErrorCode | None = None
    edited: bool = False  # saved by the person since it was read


class ProfileOut(ApiModel):
    id: str
    pack: str
    kind: Literal["individual", "organisation"]
    name: str
    summary: str
    attributes: dict[str, Any]
    tone_instructions: str
    is_default: bool
    source: ProfileSource | None = None
    reading: ProfileReading | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("source", "reading", mode="before")
    @classmethod
    def _none_when_empty(cls, value: Any) -> Any:
        return value or None


class DuplicateProfile(In):
    name: Name | None = None  # default: "<name> (copy)"


class Profiles(BaseModel):
    items: list[ProfileOut]
    next_cursor: str | None


# ─── opportunities ───────────────────────────────────────────────────────────


class Paste(In):
    """A link to a posting, or its text: one of the two."""

    pack: Key = DEFAULT_PACK
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] | None = None
    text: Annotated[str, StringConstraints(max_length=100_000)] | None = None
    # With url, from the extension: the page as the browser shows it, so it isn't fetched again.
    html: Annotated[str, StringConstraints(max_length=3_000_000)] | None = None


class Extraction(BaseModel):
    status: Literal["pending", "ready", "manual"]
    method: Literal["json_ld", "model", "manual", "import", "source"]
    error_code: ErrorCode | None = None
    edited: bool = False


class OpportunityOut(ApiModel):
    id: str
    pack: str
    title: str
    issuer_name: str
    source_url: str | None
    apply_url: str | None
    deadline: datetime | None
    status: Literal["open", "closed", "rolling", "draft"]
    attributes: dict[str, Any]
    extraction: Extraction
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class Opportunities(BaseModel):
    items: list[OpportunityOut]
    next_cursor: str | None


class OpportunityChanges(In):
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    issuer_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    apply_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^https?://\S+$")] | None
    ) = None
    deadline: datetime | None = None
    status: Literal["open", "closed", "rolling", "draft"] | None = None
    attributes: dict[str, Any] | None = None


# ─── applications ────────────────────────────────────────────────────────────


class NewApplication(In):
    opportunity_id: Id
    profile_id: Id | None = None
    notes: Text = ""


class ApplicationChanges(In):
    profile_id: Id | None = None
    notes: Text | None = None


class OpportunitySummary(ApiModel):
    id: str
    pack: str
    title: str
    issuer_name: str
    deadline: datetime | None
    apply_url: str | None
    source_url: str | None
    extraction: "Extraction"


class DocumentState(ApiModel):
    """A document in use, or one being written or failed since: enough for a card."""

    id: str
    document_type: str
    status: Literal["pending", "ready", "failed"]
    version: int


class StageRef(ApiModel):
    id: str
    code: str
    category: str


class ApplicationOut(ApiModel):
    id: str
    opportunity: OpportunitySummary
    profile_id: str | None
    pipeline_id: str
    stage: StageRef
    current_documents: list[DocumentState]
    submitted_at: datetime | None
    notes: str
    created_at: datetime
    updated_at: datetime


class Applications(BaseModel):
    items: list[ApplicationOut]
    next_cursor: str | None


class Move(In):
    stage_code: Key
    note: Annotated[str, StringConstraints(max_length=2000)] = ""


class HistoryEntry(ApiModel):
    id: str
    stage: StageRef
    entered_at: datetime
    exited_at: datetime | None
    outcome: str
    note: str


class History(BaseModel):
    items: list[HistoryEntry]


# ─── documents ───────────────────────────────────────────────────────────────


class DocumentRequest(In):
    document_type: Key
    profile_id: Id | None = None


class ClaimWarning(BaseModel):
    id: str
    kind: Literal["confirm", "number", "unsupported"]
    quote: str
    reason: str
    resolved: Literal["kept"] | None = None


class DocumentOut(ApiModel):
    id: str
    application_id: str
    document_type: str
    status: Literal["pending", "ready", "failed"]
    error_code: ErrorCode | None
    version: int
    is_active: bool
    content_markdown: str
    claim_warnings: list[ClaimWarning]
    claims_status: Literal["pending", "checked", "failed", "skipped"]
    claims_checked_at: datetime | None
    reviewed_at: datetime | None
    source: Literal["generated", "uploaded", "imported", "edited"]
    model: str | None
    generation_ms: int | None
    profile_id: str | None
    created_at: datetime
    finished_at: datetime | None


class Documents(BaseModel):
    items: list[DocumentOut]


# ─── document templates ──────────────────────────────────────────────────────

TemplateKind = Literal["sections", "letter"]
TemplateHtml = Annotated[str, StringConstraints(min_length=1, max_length=256 * 1024)]


class TemplateProblem(BaseModel):
    code: str
    message: str  # in English, saying where
    wcag: str  # the WCAG 2.2 success criterion, for an accessibility problem ("1.4.3"), else ""


class TemplateOut(BaseModel):
    kind: TemplateKind
    custom: bool  # false: the default
    filename: str
    html: str
    preview_html: str  # the template filled with a sample
    updated_at: datetime | None


class TemplateIn(In):
    html: TemplateHtml
    filename: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""


class TemplateCheck(BaseModel):
    problems: list[TemplateProblem]  # empty: it may be kept
    preview_html: str


# ─── discovery ───────────────────────────────────────────────────────────────


class SourceField(BaseModel):
    key: str
    label: Label
    hint: Label
    required: bool


class SourceKind(BaseModel):
    kind: str
    from_address: bool  # recognised from a pasted address (POST /sources/recognise), not chosen from a list
    label: Label
    description: Label
    terms: Label
    attribution: str | None
    min_interval_hours: float
    fields: list[SourceField]


class SourceKinds(BaseModel):
    items: list[SourceKind]


class SourceAddress(In):
    pack: Key = DEFAULT_PACK
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class RecognisedSource(BaseModel):
    kind: str
    config: dict[str, str]


class NewSource(In):
    pack: Key = DEFAULT_PACK
    kind: Key
    config: dict[str, str]
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    interval_hours: Annotated[float, Field(ge=1, le=24 * 7)] = 6
    enabled: bool = True


class SourceChanges(In):
    config: dict[str, str] | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    interval_hours: Annotated[float, Field(ge=1, le=24 * 7)] | None = None
    enabled: bool | None = None


class SourceOut(ApiModel):
    id: str
    pack: str
    kind: str
    name: str
    config: dict[str, str]
    enabled: bool
    interval_hours: float
    last_fetched_at: datetime | None
    last_status: Literal["never", "ok", "failed"]
    last_error_code: ErrorCode | None
    last_count: int
    created_at: datetime


class Sources(BaseModel):
    items: list[SourceOut]


class Criteria(In):
    keywords: list[Annotated[str, StringConstraints(max_length=80)]] = Field(default_factory=list, max_length=30)
    match_all: bool = False
    exclude: list[Annotated[str, StringConstraints(max_length=80)]] = Field(default_factory=list, max_length=30)
    locations: list[Annotated[str, StringConstraints(max_length=80)]] = Field(default_factory=list, max_length=20)
    remote_only: bool = False
    needs_sponsorship: bool = False
    source_ids: list[Id] = Field(default_factory=list, max_length=50)


class NewSearch(In):
    pack: Key = DEFAULT_PACK
    name: Name
    criteria: Criteria = Field(default_factory=Criteria)
    profile_id: Id | None = None
    min_score: Annotated[int, Field(ge=0, le=100)] = 0
    enabled: bool = True
    auto_enabled: bool = False  # strong matches are sent automatically (Settings → Auto), unless stopped


class SearchChanges(In):
    name: Name | None = None
    criteria: Criteria | None = None
    profile_id: Id | None = None
    min_score: Annotated[int, Field(ge=0, le=100)] | None = None
    enabled: bool | None = None
    auto_enabled: bool | None = None


class SearchOut(ApiModel):
    id: str
    pack: str
    name: str
    criteria: Criteria
    profile_id: str | None
    min_score: int
    enabled: bool
    auto_enabled: bool
    created_at: datetime


class Searches(BaseModel):
    items: list[SearchOut]


class MatchOpportunity(ApiModel):
    id: str
    pack: str
    title: str
    issuer_name: str
    status: Literal["open", "closed", "rolling", "draft"]
    source_id: str | None
    source_url: str | None
    apply_url: str | None
    posted_at: datetime | None
    deadline: datetime | None
    attributes: dict[str, Any]


class Dealbreaker(BaseModel):
    text: str
    code: str | None = None


class MatchOut(ApiModel):
    id: str
    opportunity: MatchOpportunity
    search_ids: list[str]
    status: Literal["new", "saved", "dismissed", "tracked"]
    prefilter: dict[str, Any]
    score: int | None
    score_reasons: list[str]
    dealbreakers: list[Dealbreaker]
    score_status: Literal["pending", "scored", "failed", "capped"]
    score_error_code: ErrorCode | None
    scored_at: datetime | None
    model: str | None
    application_id: str | None
    created_at: datetime


class MatchCounts(BaseModel):
    new: int
    saved: int
    dismissed: int
    tracked: int


class Matches(BaseModel):
    items: list[MatchOut]
    next_cursor: str | None
    counts: MatchCounts


class MatchChanges(In):
    status: Literal["new", "saved", "dismissed"]


class Tracked(BaseModel):
    match: MatchOut
    application_id: str


class BriefingMatch(BaseModel):
    pack: str = DEFAULT_PACK  # briefings built before packs existed didn't say
    match_id: str
    opportunity_id: str
    title: str
    issuer_name: str
    score: int | None


class BriefingFollowUp(BaseModel):
    pack: str = DEFAULT_PACK  # briefings built before packs existed didn't say
    application_id: str
    title: str
    issuer_name: str
    stage_code: str
    days: int


class BriefingDeadline(BaseModel):
    pack: str = DEFAULT_PACK  # briefings built before packs existed didn't say
    application_id: str
    title: str
    issuer_name: str
    deadline: datetime


class BriefingNewMatches(BaseModel):
    count: int
    top: list[BriefingMatch]


class BriefingContent(BaseModel):
    new_matches: BriefingNewMatches
    follow_ups: list[BriefingFollowUp]
    deadlines: list[BriefingDeadline]


class BriefingOut(ApiModel):
    date: str
    content: BriefingContent
    created_at: datetime


# ─── review and the Application kit ──────────────────────────────────────────


class DocumentContent(In):
    content_markdown: Annotated[str, StringConstraints(min_length=1, max_length=100_000)]


class WarningResolution(In):
    resolution: Literal["kept", "open"]


class Reviewed(In):
    reviewed: bool = True


class Choice(BaseModel):
    value: str
    label: Label


class AnswerOut(ApiModel):
    id: str
    pack: str
    key: str
    question: Label
    answer: str
    answer_type: Literal["text", "yes_no", "choice", "number", "url"]
    choices: list[Choice]
    is_sensitive: bool
    source: Literal["user", "learned", "pack"]


class Answers(BaseModel):
    items: list[AnswerOut]


class NewAnswer(In):
    pack: Key = DEFAULT_PACK
    key: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,79}$")]
    question: dict[Locale, Annotated[str, StringConstraints(min_length=1, max_length=500)]]
    answer: Annotated[str, StringConstraints(max_length=5000)] = ""
    answer_type: Literal["text", "yes_no", "number", "url"] = "text"
    is_sensitive: bool = False


class AnswerChanges(In):
    answer: Annotated[str, StringConstraints(max_length=5000)] | None = None
    question: dict[Locale, Annotated[str, StringConstraints(min_length=1, max_length=500)]] | None = None
    is_sensitive: bool | None = None


class AddedDefaults(BaseModel):
    added: int


class KitDocument(BaseModel):
    document: DocumentOut
    label: Label
    open_warnings: int


class SubmissionOut(ApiModel):
    id: str
    application_id: str
    channel: Literal["manual", "extension", "auto"]
    submitted_at: datetime
    documents: list[dict[str, Any]]
    answers: list[dict[str, Any]]
    note: str
    details: dict[str, Any] = Field(default_factory=dict)
    undone_at: datetime | None


class Kit(BaseModel):
    application: ApplicationOut
    apply_url: str | None
    documents: list[KitDocument]
    answers: list[AnswerOut]
    submissions: list[SubmissionOut]


class Filled(In):
    """What the extension did to the form: counts and labels only, never the values."""

    fields: int = Field(default=0, ge=0, le=1000)
    files: list[Annotated[str, StringConstraints(max_length=60)]] = Field(default_factory=list, max_length=20)
    left_blank: list[Annotated[str, StringConstraints(max_length=300)]] = Field(default_factory=list, max_length=100)


class NewSubmission(In):
    note: Annotated[str, StringConstraints(max_length=2000)] = ""
    # From the extension: the board's confirmation page, and what it filled.
    confirmation_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^https?://\S+$")] | None
    ) = None
    filled: Filled | None = None


# ─── the extension's copy panel ──────────────────────────────────────────────


class CopyItemOut(BaseModel):
    label: dict[str, str]
    value: str
    sensitive: bool = Field(description="An equal-opportunity answer: shown only after the person asks")


class CopyGroupOut(BaseModel):
    title: str = Field(description="The person's own words for the entry (a job, a qualification), or empty")
    items: list[CopyItemOut]


class CopyTabOut(BaseModel):
    key: str
    label: dict[str, str]
    groups: list[CopyGroupOut]


class CopyProfile(BaseModel):
    id: str
    pack: str
    name: str
    is_default: bool


class CopySheetOut(BaseModel):
    """A profile's values, each ready to copy and paste into any form; no profile yet: profile null."""

    profile: CopyProfile | None
    profiles: list[CopyProfile]
    tabs: list[CopyTabOut]


# ─── personal API tokens and the extension ───────────────────────────────────

Scope = Literal["applications:read", "applications:write", "submissions:write", "profiles:read"]
TokenKind = Literal["extension", "agent"]  # agent: an AI agent through `apply mcp`; it can't record submissions


class NewToken(In):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    kind: TokenKind = "extension"
    scopes: list[Scope] = Field(min_length=1, max_length=4)
    expires_in_days: Literal[30, 90, 365] | None = 90  # None: never


class TokenOut(ApiModel):
    id: str
    name: str
    kind: TokenKind
    prefix: str
    scopes: list[Scope]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class CreatedToken(BaseModel):
    token: TokenOut
    secret: str = Field(description="Shown this once; only its hash is kept")


class Tokens(BaseModel):
    items: list[TokenOut]


class Caller(BaseModel):
    """Who a request is: the owner, and the token it came with (None for a session)."""

    email: str
    locale: Locale
    token: TokenOut | None
    web_url: str | None = Field(default=None, description="The web app, for links back to it")


class Lookup(BaseModel):
    opportunity: OpportunityOut
    application: ApplicationOut | None


class FillDocument(BaseModel):
    document_id: str
    document_type: str
    label: Label
    version: int
    filename: str
    pdf_path: str
    reviewed: bool
    open_warnings: int


class FillSheet(BaseModel):
    """Everything the extension puts into a form. Sensitive answers go only to the form, never to a model."""

    application: ApplicationOut
    opportunity: OpportunityOut
    values: dict[str, str]
    answers: list[AnswerOut]
    documents: list[FillDocument]


# ─── Auto ────────────────────────────────────────────────────────────────────

RunStatus = Literal["starting", "writing", "ready", "sent", "needs_you", "stopped", "dismissed"]


class AutoSettings(ApiModel):
    auto_paused: bool
    auto_min_score: int
    auto_daily_cap: int


class AutoSettingsChanges(In):
    auto_paused: bool | None = None
    auto_min_score: Annotated[int, Field(ge=0, le=100)] | None = None
    auto_daily_cap: Annotated[int, Field(ge=0, le=50)] | None = None


class AutoScreenshotRef(BaseModel):
    id: str
    step: str
    size: int


class AutoRunOut(BaseModel):
    id: str
    status: RunStatus
    reason: ErrorCode | None
    reason_detail: dict[str, Any]
    match_id: str
    application_id: str | None
    search_id: str | None
    opportunity: OpportunitySummary
    score: int | None
    ready_at: datetime | None = Field(description="When it was prepared: the person's to send from then")
    drafts: list[dict[str, Any]] = Field(description="Answers a runner drafted, on runs from before (history)")
    screenshots: list[AutoScreenshotRef] = Field(description="A runner's screenshots, on runs from before")
    submission_id: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


class AutoRuns(BaseModel):
    items: list[AutoRunOut]


class AutoCounts(BaseModel):
    waiting: int = Field(description="Being prepared")
    ready: int = Field(description="Prepared: the person's to send")
    needs_you: int
    sent: int
