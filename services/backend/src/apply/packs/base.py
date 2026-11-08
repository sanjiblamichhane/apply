"""
What a pack is: the few things that are genuinely different between applying for a job, a tender or a grant.

The engine (models, endpoints, queue, screens) is shared. A pack adds only:

- its key, labels, and the kinds of profile that apply with it;
- pydantic models for a profile's and an opportunity's ``attributes``;
- its document types, each with a prompt when it can be written by the model;
- its default pipeline;
- how to read an opportunity: from JSON-LD on a page, and from text by the model.

A pack is a Python object registered under the ``apply.packs`` entry point (built-in packs are registered
directly), so a pack can live in its own package.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from importlib import resources
from typing import Any, ClassVar, Literal

from annotated_types import MaxLen
from pydantic import BaseModel, Field, ValidationError

from apply.errors import ErrorCode, InvalidArgument, NotFound
from apply.i18n import Label, label
from apply.libs.llm import GENERAL

Category = Literal["pre_pipeline", "active", "success", "failure", "paused"]
ActionType = Literal["passive", "document", "interview", "test", "decision", "negotiation", "follow_up"]
ProfileKind = Literal["individual", "organisation"]

CATEGORY_LABELS: dict[str, Label] = {
    "pre_pipeline": label("Not started", "सुरु नभएको"),
    "active": label("In progress", "चलिरहेको"),
    "success": label("Won", "सफल"),
    "failure": label("Lost", "असफल"),
    "paused": label("On hold", "रोकिएको"),
}
ACTION_LABELS: dict[str, Label] = {
    "passive": label("Waiting", "पर्खाइमा"),
    "document": label("Documents needed", "कागजात चाहिन्छ"),
    "interview": label("Interview", "अन्तर्वार्ता"),
    "test": label("Assessment", "परीक्षा"),
    "decision": label("Decision", "निर्णय"),
    "negotiation": label("Negotiation", "वार्ता"),
    "follow_up": label("Follow up", "फलो-अप गर्नुहोस्"),
}
PROFILE_KIND_LABELS: dict[str, Label] = {
    "individual": label("Person", "व्यक्ति"),
    "organisation": label("Organisation", "संस्था"),
}


@dataclass(frozen=True)
class StageSpec:
    code: str
    label: Label
    category: Category
    action_type: ActionType = "passive"
    is_terminal: bool = False
    follow_up_after_days: int | None = None
    expected_duration_days: int | None = None


@dataclass(frozen=True)
class PipelineSpec:
    key: str
    label: Label
    stages: tuple[StageSpec, ...]


@dataclass(frozen=True)
class DocumentTypeSpec:
    key: str
    label: Label
    description: Label
    generatable: bool
    accepts_upload: bool = True
    prompt: str | None = None  # the file in the pack's prompts/ folder
    layout: Literal["sections", "letter"] = "sections"  # its parts in the template (libs/render/template.py)


@dataclass(frozen=True)
class Extracted:
    """An opportunity as read from a page or by the model, before it is saved."""

    title: str
    issuer_name: str
    attributes: dict[str, Any]
    apply_url: str | None = None
    deadline: datetime | None = None
    status: str = "open"


@dataclass(frozen=True)
class CopyItem:
    """One value the extension's copy panel offers: clicked, it's on the clipboard."""

    label: Label
    value: str
    sensitive: bool = False  # shown only after "Show"


@dataclass(frozen=True)
class CopyGroup:
    """Values that belong together (one job, one qualification); title is the person's own words, or ""."""

    title: str
    items: list[CopyItem]


@dataclass(frozen=True)
class CopyTab:
    key: str
    label: Label
    groups: list[CopyGroup]


COPY_TABS: dict[str, Label] = {
    "basics": label("Basics", "आधारभूत"),
    "more": label("More", "थप"),
    "answers": label("Answers", "जवाफहरू"),
}
COPY_LABELS: dict[str, Label] = {
    "summary": label("Summary", "सारांश"),
    "one_per_line": label("{field}, one per line", "{field}, एक लाइनमा एउटा"),
    "comma": label("{field}, with commas", "{field}, अल्पविरामसहित"),
}


def copy_label(key: str, **values: Label) -> Label:
    """A copy label with its {field} filled in each language."""
    return {
        lang: text.format(**{name: value.get(lang) or value["en"] for name, value in values.items()})
        for lang, text in COPY_LABELS[key].items()
    }


def _list_items(title: Label, values: list[str]) -> list[CopyItem]:
    """A list of text, as forms ask for it: one per line, and with commas (short items only)."""
    if not values:
        return []
    items = [CopyItem(copy_label("one_per_line", field=title), "\n".join(values))]
    if all(len(v) <= 80 for v in values):
        items.append(CopyItem(copy_label("comma", field=title), ", ".join(values)))
    return items


def _inner_model(annotation: Any) -> type[BaseModel] | None:
    """The model of a list[Model] field's entries."""
    for arg in getattr(annotation, "__args__", ()) or ():
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def _entry_group(entry: dict[str, Any], model: type[BaseModel] | None) -> CopyGroup:
    """One entry of a list (a job, a qualification): each of its fields, titled by its first two."""
    items: list[CopyItem] = []
    fields = model.model_fields if model else {k: None for k in entry}
    for name, field in fields.items():
        extra = field.json_schema_extra if field is not None and isinstance(field.json_schema_extra, dict) else {}
        title: Label = extra.get("x-label") or {"en": name}  # type: ignore[assignment]
        value = entry.get(name)
        if isinstance(value, str) and value.strip():
            items.append(CopyItem(title, value.strip()))
        elif isinstance(value, list) and value:
            lines = [str(v).strip() for v in value if str(v).strip()]
            if lines:
                items.append(CopyItem(title, "\n".join(f"• {line}" for line in lines)))
    heading = ", ".join(i.value for i in items[:2] if "\n" not in i.value)
    return CopyGroup(heading, items)


@dataclass(frozen=True)
class ProfileInput:
    name: str
    summary: str
    attributes: dict[str, Any]
    tone_instructions: str = ""


@dataclass(frozen=True)
class OpportunityInput:
    title: str
    issuer_name: str
    attributes: dict[str, Any]
    source_text: str = ""


@dataclass(frozen=True)
class Prompt:
    text: str
    purpose: str  # libs.llm purposes: writing, score, check, general


# ─── discovery: sources, searching, scoring ──────────────────────────────────


# Questions no model may answer for anyone, in any pack: who someone is, not what they've done. Matched on a
# form's own label, so a question the pack didn't foresee is still caught. Used by Auto's drafting.
# The same topics in Spanish: stems match at a word's start ("discapacid" → discapacidad), and a word under four
# letters (dni, nie) only whole. Over-matching is the safe side: such a question is left for the person.
SENSITIVE_ES = (
    "género",
    "genero",
    "sexo",
    "sexual",
    "orientación sexual",
    "identidad de género",
    "raza",
    "racial",
    "étnic",
    "etnic",
    "etnia",
    "origen étnico",
    "discapacid",
    "minusval",
    "diversidad funcional",
    "veteran",
    "militar",
    "fuerzas armadas",
    "religi",
    "creencia",
    "credo",
    "pronombre",
    "fecha de nacimiento",
    "nacimiento",
    "edad",
    "años de edad",
    "estado civil",
    "casad",
    "soltero",
    "soltera",
    "embaraz",
    "gestación",
    "maternidad",
    "antecedentes penales",
    "condena",
    "delito",
    "penal",
    "documento de identidad",
    "dni",
    "nie",
    "curp",
    "rfc",
    "cédula",
    "cedula",
    "seguridad social",
    "número de seguro social",
    "seguro social",
    "pasaporte",
    "casta",
    "nacionalidad",
    "ciudadanía",
    "ciudadania",
    "salud",
    "médic",
    "medic",
    "enfermedad",
    "sanitari",
)


def _words(words: tuple[str, ...]) -> str:
    return "|".join(rf"\b{re.escape(w)}\b" if len(w) < 4 else rf"\b{re.escape(w)}" for w in words)


SENSITIVE_QUESTION = re.compile(
    r"\b(gender|sex|sexual|race|racial|ethnic\w*|disabilit\w*|disabled|veteran|religio\w*|belief|pronoun\w*|"
    r"date of birth|birth ?date|age|marital|pregnan\w*|criminal|convict\w*|national insurance|social security|"
    r"ssn|caste|nationality|citizenship|health|medical)\b|लिङ्ग|जात|अपाङ्ग|धर्म|उमेर|वैवाहिक|" + _words(SENSITIVE_ES),
    re.I,
)


def labelled(en: str, ne: str, *, options: dict[str, Label] | None = None, long: bool = False, **field: Any) -> Any:
    """
    A pack model's field with what a person reads for it, in the JSON schema the screens draw from:
    ``x-label`` (en, ne), ``x-options`` for an enum's values, ``x-long`` for text that wants a big box.

        name: Short = labelled("Legal name", "कानुनी नाम", default="")
    """
    extra: dict[str, Any] = {"x-label": label(en, ne)}
    if options:
        extra["x-options"] = {k: dict(v) for k, v in options.items()}
    if long:
        extra["x-long"] = True
    return Field(json_schema_extra=extra, **field)


def schema_labels(schema: dict[str, Any], prefix: str) -> dict[str, Label]:
    """Every x-label and x-options label in a model's JSON schema (nested models too), keyed by path."""
    found: dict[str, Label] = {}
    defs = schema.get("$defs", {})

    def walk(node: dict[str, Any], path: str) -> None:
        for name, prop in (node.get("properties") or {}).items():
            here = f"{path}.{name}"
            if "x-label" in prop:
                found[here] = prop["x-label"]
            for value, option in (prop.get("x-options") or {}).items():
                found[f"{here}.{value}"] = option
            for ref in _refs(prop):
                walk(defs.get(ref, {}), here)

    walk(schema, prefix)
    return found


def _refs(prop: dict[str, Any]) -> list[str]:
    out = []
    for node in (prop, prop.get("items") or {}, *(prop.get("anyOf") or [])):
        ref = node.get("$ref") if isinstance(node, dict) else None
        if ref:
            out.append(ref.rsplit("/", 1)[-1])
    return out


@dataclass(frozen=True)
class ConfigField:
    """One setting a source needs (a board's token, a search query), as a form shows it."""

    key: str
    label: Label
    hint: Label
    required: bool = True
    pattern: str = r"^[A-Za-z0-9_.\-]{1,100}$"


@dataclass(frozen=True)
class Listing:
    """One posting as a source lists it, already in the pack's fields."""

    ref: str  # unique within the source (the board's own id)
    title: str
    issuer_name: str
    attributes: dict[str, Any]
    source_url: str
    apply_url: str
    posted_at: datetime | None = None
    deadline: datetime | None = None
    source_text: str = ""


class SourceAdapter(ABC):
    """
    A public listings API (a job board's, a tender portal's). Adapters only use APIs published for this, at no
    more than the rate their terms ask (``min_interval_hours``), through apply's safe fetcher.
    """

    kind: ClassVar[str]
    label: ClassVar[Label]
    description: ClassVar[Label]
    terms: ClassVar[Label]  # what its terms ask of us (attribution, rate), shown with the source
    attribution: ClassVar[str | None] = None  # shown with each listing, where the terms ask for it
    min_interval_hours: ClassVar[float] = 1.0
    # Addresses a person may paste for this kind (a company's own job board page): patterns whose named groups are
    # config keys. Empty: chosen by kind instead.
    addresses: ClassVar[tuple[re.Pattern[str], ...]] = ()
    default_base_url: ClassVar[str]
    config_fields: ClassVar[tuple[ConfigField, ...]]

    def validate_config(self, config: dict[str, Any]) -> dict[str, str]:
        clean: dict[str, str] = {}
        for spec in self.config_fields:
            value = str(config.get(spec.key, "") or "").strip()
            if not value:
                if spec.required:
                    raise InvalidArgument(
                        ErrorCode.INVALID_ATTRIBUTES,
                        f"{spec.key} is needed",
                        extra={"errors": [{"loc": ["config", spec.key], "msg": "required", "type": "missing"}]},
                    )
                continue
            if not re.match(spec.pattern, value):
                raise InvalidArgument(
                    ErrorCode.INVALID_ATTRIBUTES,
                    f"{spec.key} doesn't look right",
                    extra={"errors": [{"loc": ["config", spec.key], "msg": "invalid", "type": "pattern"}]},
                )
            clean[spec.key] = value
        return clean

    @abstractmethod
    def display_name(self, config: dict[str, str]) -> str: ...

    @abstractmethod
    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]: ...

    def recognise(self, url: str) -> dict[str, str] | None:
        """The config an address stands for, when it's one of this kind's; None otherwise."""
        for pattern in self.addresses:
            if found := pattern.match(url.strip()):
                return {key: value for key, value in found.groupdict().items() if value}
        return None

    def describe(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "from_address": bool(self.addresses),
            "label": dict(self.label),
            "description": dict(self.description),
            "terms": dict(self.terms),
            "attribution": self.attribution,
            "min_interval_hours": self.min_interval_hours,
            "fields": [
                {"key": f.key, "label": dict(f.label), "hint": dict(f.hint), "required": f.required}
                for f in self.config_fields
            ],
        }


@dataclass(frozen=True)
class QuestionSpec:
    """A question application forms ask, with the answer kept for next time (plan §4, answers)."""

    key: str
    question: Label
    answer_type: Literal["text", "yes_no", "choice", "number", "url"] = "text"
    choices: tuple[tuple[str, Label], ...] = ()
    sensitive: bool = False  # never sent to a model; "decline" unless the person answers
    default: str = ""


@dataclass(frozen=True)
class Searchable:
    """What a search's rules look at, whatever the pack calls its fields."""

    title: str
    body: str
    location: str
    remote: bool
    sponsorship: str


class Pack(ABC):
    key: ClassVar[str]
    version: ClassVar[str]
    label: ClassVar[Label]
    description: ClassVar[Label]
    profile_kinds: ClassVar[tuple[ProfileKind, ...]]
    profile_model: ClassVar[type[BaseModel]]
    opportunity_model: ClassVar[type[BaseModel]]
    document_types: ClassVar[tuple[DocumentTypeSpec, ...]]
    pipeline: ClassVar[PipelineSpec]
    json_ld_types: ClassVar[frozenset[str]] = frozenset()
    prompts_package: ClassVar[str]  # e.g. "apply.packs.job.prompts"
    # Which of a search's options mean something for this pack (the search form shows only these).
    search_options: ClassVar[frozenset[Literal["locations", "remote_only", "needs_sponsorship"]]] = frozenset(
        {"locations"}
    )
    # Whether Auto prepares strong matches in this pack (it never sends: the person does).
    auto: ClassVar[bool] = False

    # ── documents ────────────────────────────────────────────────────────────

    def document_type(self, key: str) -> DocumentTypeSpec:
        for spec in self.document_types:
            if spec.key == key:
                return spec
        raise NotFound(ErrorCode.DOCUMENT_TYPE_NOT_FOUND, f"The {self.key} pack has no document type {key!r}")

    def prompt_template(self, name: str) -> str:
        return resources.files(self.prompts_package).joinpath(name).read_text(encoding="utf-8")

    @abstractmethod
    def document_prompt(
        self, document_type: str, profile: ProfileInput, opportunity: OpportunityInput, today: date
    ) -> Prompt: ...

    # ── attributes ───────────────────────────────────────────────────────────

    def validate_profile(self, attributes: dict[str, Any]) -> dict[str, Any]:
        return _validate(self.profile_model, attributes)

    def validate_opportunity(self, attributes: dict[str, Any]) -> dict[str, Any]:
        return _validate(self.opportunity_model, attributes)

    @abstractmethod
    def describe(self, attributes: dict[str, Any]) -> tuple[str, str]:
        """An opportunity's (title, issuer name) from its attributes."""

    # ── reading an opportunity ───────────────────────────────────────────────

    @abstractmethod
    def from_json_ld(self, node: dict[str, Any], page_url: str) -> Extracted | None: ...

    @abstractmethod
    def extraction_prompt(self, text: str) -> Prompt: ...

    @abstractmethod
    def extraction_schema(self) -> dict[str, Any]: ...

    @abstractmethod
    def from_extraction(self, data: dict[str, Any]) -> Extracted: ...

    # ── reading a profile from a document (a resume, a capability statement) ─

    # What such a document is called in the reading prompt.
    profile_document: ClassVar[str] = "document describing someone who applies"

    def reading_schema(self) -> dict[str, Any]:
        """What the model returns: a summary, and the pack's profile fields (every one, empty when not stated)."""
        return {
            "type": "object",
            "properties": {"summary": {"type": "string"}, "profile": plain_schema(self.profile_model)},
            "required": ["summary", "profile"],
        }

    def reading_prompt(self, text: str) -> Prompt:
        fields = "\n".join(f"- {path}: {name}" for path, name in field_guide(self.profile_model))
        body = fill(
            resources.files(COMMON_PROMPTS).joinpath("read_profile.md").read_text(encoding="utf-8"),
            document=self.profile_document,
            fields=fields,
            text=text,
        )
        return Prompt(text=body, purpose=GENERAL)

    def from_reading(self, data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """(summary, attributes) from the model's reading. What doesn't fit the fields is dropped, never fixed up."""
        summary = data.get("summary")
        summary = " ".join(summary.split())[:SUMMARY_MAX] if isinstance(summary, str) else ""
        profile = data.get("profile")
        return summary, keep_what_fits(self.profile_model, profile if isinstance(profile, dict) else {})

    # ── discovery ────────────────────────────────────────────────────────────

    sources: ClassVar[tuple[SourceAdapter, ...]] = ()

    def source(self, kind: str) -> SourceAdapter:
        for adapter in self.sources:
            if adapter.kind == kind:
                return adapter
        raise NotFound(ErrorCode.SOURCE_KIND_NOT_FOUND, f"The {self.key} pack has no source {kind!r}")

    @abstractmethod
    def searchable(self, title: str, attributes: dict[str, Any]) -> Searchable: ...

    @abstractmethod
    def dedupe_key(self, issuer_name: str, title: str, attributes: dict[str, Any]) -> str:
        """The same opportunity from two sources has the same key (normalised issuer, title, place)."""

    @abstractmethod
    def score_prompt(self, profile: ProfileInput, opportunity: OpportunityInput) -> Prompt: ...

    # ── review and applying ──────────────────────────────────────────────────

    standard_questions: ClassVar[tuple[QuestionSpec, ...]] = ()
    submitted_stage: ClassVar[str | None] = None  # where a "New" application goes once submitted

    def form_values(self, profile: ProfileInput) -> dict[str, str]:
        """
        What a form's standard fields get from the profile, by the keys packages/ats-adapters knows
        (full_name, first_name, last_name, email, phone, location, linkedin, github, website, …). Empty ones
        are left out.
        """
        return {"full_name": profile.name} if profile.name else {}

    def is_sensitive_question(self, label: str) -> bool:
        """Whether a form's question is one no model may answer: by its words, or as one of the pack's own."""
        text = " ".join(label.split()).lower()
        if SENSITIVE_QUESTION.search(text):
            return True
        return any(
            q.sensitive and text in {v.lower() for v in q.question.values() if v} for q in self.standard_questions
        )

    def copy_sheet(self, profile: ProfileInput) -> list[CopyTab]:
        """
        The extension's copy panel, from the profile model's own fields and labels: text in Basics, lists of
        text in More (one per line and with commas), and each list of entries (experience, past contracts…) in
        a tab of its own with one group per entry. A pack overrides it for values forms ask for in pieces.
        """
        attrs = profile.attributes
        basics: list[CopyItem] = []
        more: list[CopyItem] = []
        listed: list[CopyTab] = []
        for name, field in self.profile_model.model_fields.items():
            extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
            title: Label = extra.get("x-label") or {"en": name}  # type: ignore[assignment]
            value = attrs.get(name)
            if isinstance(value, str) and value.strip():
                basics.append(CopyItem(title, value.strip()))
            elif isinstance(value, list) and value and all(isinstance(v, str) for v in value):
                more += _list_items(title, [v for v in value if v.strip()])
            elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                inner = _inner_model(field.annotation)
                listed.append(
                    CopyTab(name, title, [_entry_group(entry, inner) for entry in value if any(entry.values())])
                )
        if profile.summary.strip():
            more.insert(0, CopyItem(COPY_LABELS["summary"], profile.summary.strip()))
        tabs = [CopyTab("basics", COPY_TABS["basics"], [CopyGroup("", basics)])] if basics else []
        tabs += listed
        if more:
            tabs.append(CopyTab("more", COPY_TABS["more"], [CopyGroup("", more)]))
        return tabs

    def letterhead(self, profile: ProfileInput) -> tuple[str, str]:
        """
        A document's header, from the profile rather than the model: the name, and the contact line as markdown
        ("Denton, TX | Phone: [940-555-0100](tel:+19405550100) | Email: [sam@example.com](mailto:…)"). ("", "")
        leaves the model's own.
        """
        return "", ""

    def person_name(self, profile: ProfileInput) -> str:
        """Who the documents are from (a PDF's author, the files' names), or "" if the profile doesn't say."""
        return ""

    def claims_prompt(self, document_markdown: str, profile: ProfileInput) -> Prompt:
        person = {"name": profile.name, "summary": profile.summary, **profile.attributes}
        text = fill(self.prompt_template("claims.md"), document=document_markdown[:30_000], profile=as_json(person))
        return Prompt(text=text, purpose="check")

    claims_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {"quote": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["quote", "reason"],
                },
            },
        },
        "required": ["claims"],
    }

    score_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "dealbreakers": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        },
        "required": ["fit_score", "reasons", "dealbreakers"],
    }

    # ── for the registry, the API and the i18n test ─────────────────────────

    def labels(self) -> dict[str, Label]:
        """Every label this pack shows, keyed for the i18n completeness test."""
        found: dict[str, Label] = {
            f"{self.key}.label": self.label,
            f"{self.key}.description": self.description,
            f"{self.key}.pipeline.{self.pipeline.key}": self.pipeline.label,
        }
        for spec in self.document_types:
            found[f"{self.key}.document.{spec.key}"] = spec.label
            found[f"{self.key}.document.{spec.key}.description"] = spec.description
        for stage in self.pipeline.stages:
            found[f"{self.key}.stage.{stage.code}"] = stage.label
        for question in self.standard_questions:
            found[f"{self.key}.question.{question.key}"] = question.question
            for value, choice in question.choices:
                found[f"{self.key}.question.{question.key}.{value}"] = choice
        found |= schema_labels(self.profile_model.model_json_schema(), f"{self.key}.profile")
        found |= schema_labels(self.opportunity_model.model_json_schema(), f"{self.key}.opportunity")
        for adapter in self.sources:
            found[f"{self.key}.source.{adapter.kind}"] = adapter.label
            found[f"{self.key}.source.{adapter.kind}.description"] = adapter.description
            found[f"{self.key}.source.{adapter.kind}.terms"] = adapter.terms
            for spec in adapter.config_fields:
                found[f"{self.key}.source.{adapter.kind}.{spec.key}"] = spec.label
                found[f"{self.key}.source.{adapter.kind}.{spec.key}.hint"] = spec.hint
        return found

    def registry_row(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "version": self.version,
            "label": dict(self.label),
            "description": dict(self.description),
            "profile_schema": self.profile_model.model_json_schema(),
            "opportunity_schema": self.opportunity_model.model_json_schema(),
            "document_types": [
                {
                    "key": d.key,
                    "label": dict(d.label),
                    "description": dict(d.description),
                    "generatable": d.generatable,
                    "accepts_upload": d.accepts_upload,
                    "layout": d.layout,
                }
                for d in self.document_types
            ],
        }


def _validate(model: type[BaseModel], attributes: dict[str, Any]) -> dict[str, Any]:
    try:
        return model.model_validate(attributes).model_dump(mode="json")
    except ValidationError as exc:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        raise InvalidArgument(
            ErrorCode.INVALID_ATTRIBUTES, "The attributes don't fit the pack's fields", extra={"errors": errors}
        ) from exc


# ── a pack's profile fields, for the model ──────────────────────────────────

COMMON_PROMPTS = "apply.packs.common.prompts"
SUMMARY_MAX = 2_000
_SCHEMA_KEYS = ("type", "enum")


def plain_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    The model's JSON Schema as a model server's structured output takes it: references inlined, only types,
    enums, properties and items kept, and every property required (an empty value when the document doesn't say).
    """
    root = model.model_json_schema()
    defs = root.get("$defs", {})

    def walk(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            return walk(defs[node["$ref"].rsplit("/", 1)[-1]])
        if "anyOf" in node:
            return walk(next(n for n in node["anyOf"] if n.get("type") != "null"))
        out = {k: node[k] for k in _SCHEMA_KEYS if k in node}
        if node.get("type") == "object" or "properties" in node:
            props = {name: walk(prop) for name, prop in node.get("properties", {}).items()}
            out |= {"type": "object", "properties": props, "required": list(props)}
        if "items" in node:
            out["items"] = walk(node["items"])
        return out

    return walk(root)


def field_guide(model: type[BaseModel]) -> list[tuple[str, str]]:
    """(path, English label) for each field, nested ones as ``experience[].title``: the prompt's list of fields."""
    root = model.model_json_schema()
    defs = root.get("$defs", {})
    found: list[tuple[str, str]] = []

    def walk(node: dict[str, Any], path: str) -> None:
        for name, prop in node.get("properties", {}).items():
            here = f"{path}{name}"
            found.append((here, prop.get("x-label", {}).get("en", name)))
            target = prop.get("items", prop)
            if "$ref" in target:
                walk(defs[target["$ref"].rsplit("/", 1)[-1]], f"{here}[]." if "items" in prop else f"{here}.")

    walk(root, "")
    return found


def keep_what_fits(model: type[BaseModel], data: dict[str, Any]) -> dict[str, Any]:
    """
    The fields of ``data`` that fit ``model``, each checked on its own: a list keeps the items that fit, and a
    field or item that doesn't is left out (so the person fills it in), never guessed at or cut to fit.
    """
    blank = model.model_construct()
    validator = model.__pydantic_validator__

    def fits(name: str, value: Any) -> bool:
        try:
            validator.validate_assignment(blank.model_copy(), name, value)
        except ValidationError:
            return False
        return True

    kept: dict[str, Any] = {}
    for name, value in data.items():
        if name not in model.model_fields:
            continue
        if isinstance(value, list):
            value = [item for item in value if not _empty(item) and fits(name, [item])]
            longest = next((m.max_length for m in model.model_fields[name].metadata if isinstance(m, MaxLen)), None)
            value = value[:longest] if longest is not None else value  # a list's limit keeps the first ones
        if fits(name, value):
            kept[name] = value
    return _validate(model, kept)


def _empty(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_empty(v) for v in value.values())
    if isinstance(value, list):
        return all(_empty(v) for v in value)
    return value is None or (isinstance(value, str) and not value.strip())


def as_json(value: Any) -> str:
    """Data for a prompt: readable, and never re-read as a template (values are substituted, not formatted)."""
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)


_SLOT = re.compile(r"\{\{([a-z_]+)\}\}")


def fill(template: str, **values: str) -> str:
    """
    A prompt file with ``{{name}}`` slots, filled in one pass: a value is put in as it is and never read again
    as part of the template, so a posting that contains ``{{…}}`` changes nothing.
    """
    missing = set(_SLOT.findall(template)) - values.keys()
    if missing:
        raise ValueError(f"Prompt slots left unfilled: {sorted(missing)}")
    return _SLOT.sub(lambda m: values[m.group(1)], template)
