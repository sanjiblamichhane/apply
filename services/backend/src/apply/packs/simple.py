"""
A pack mostly described by data: its models (with x-labels), documents, pipeline and questions, plus a few
field names. Extraction, scoring, searching and de-duplicating follow from those; writing uses the pack's own
prompts. The tender, grant and contract packs are built on it; a pack can override any of it.

Prompts the pack doesn't have (score.md, extract.md, claims.md) come from packs/common/prompts.
"""

import re
import unicodedata
from datetime import date
from importlib import resources
from typing import Any, ClassVar

from apply.i18n import Label
from apply.libs.llm import GENERAL, SCORE, WRITING

from .base import COMMON_PROMPTS, Extracted, OpportunityInput, Pack, ProfileInput, Prompt, Searchable, as_json, fill

DESCRIPTION_LIMIT = 24_000
SCORE_LIMIT = 12_000


def normalise(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    plain = re.sub(r"\b(inc|ltd|llc|gmbh|pvt|plc|co|limited)\b\.?", "", plain)
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


class DeclarativePack(Pack):
    """Set the class variables; override a method only where the pack really differs."""

    # What the pack calls one opportunity, in a sentence: "a public tender", "a grant".
    noun: ClassVar[Label]
    # Which of the opportunity model's fields hold these (the description is markdown).
    title_field: ClassVar[str] = "title"
    issuer_field: ClassVar[str]
    description_field: ClassVar[str] = "description_markdown"
    location_field: ClassVar[str | None] = None
    reference_field: ClassVar[str | None] = None
    remote_field: ClassVar[str | None] = None  # a field whose value "remote" means remote work
    # Which of the profile model's fields names who the documents are from.
    name_field: ClassVar[str | None] = None

    def prompt_template(self, name: str) -> str:
        own = resources.files(self.prompts_package).joinpath(name)
        if own.is_file():
            return own.read_text(encoding="utf-8")
        return resources.files(COMMON_PROMPTS).joinpath(name).read_text(encoding="utf-8")

    def person_name(self, profile: ProfileInput) -> str:
        return str(profile.attributes.get(self.name_field) or "").strip() if self.name_field else ""

    # ── the opportunity's fields ─────────────────────────────────────────────

    def _properties(self) -> dict[str, dict[str, Any]]:
        return self.opportunity_model.model_json_schema().get("properties", {})

    def describe(self, attributes: dict[str, Any]) -> tuple[str, str]:
        return str(attributes.get(self.title_field) or ""), str(attributes.get(self.issuer_field) or "")

    def opportunity_block(self, opportunity: OpportunityInput, limit: int) -> str:
        """The opportunity for a prompt: each field the notice gave, by its English label, then the description."""
        attrs = opportunity.attributes
        lines = [f"Title: {attrs.get(self.title_field) or opportunity.title}"]
        lines.append(f"From: {attrs.get(self.issuer_field) or opportunity.issuer_name}")
        for key, prop in self._properties().items():
            if key in (self.title_field, self.issuer_field, self.description_field):
                continue
            value = attrs.get(key)
            if value not in (None, "", []):
                label = prop.get("x-label", {}).get("en", key)
                options = prop.get("x-options") or {}
                shown = options.get(value, {}).get("en", value) if isinstance(value, str) else value
                lines.append(f"{label}: {shown}")
        description = attrs.get(self.description_field) or opportunity.source_text
        lines.append(f"Description:\n{str(description)[:limit]}")
        return "\n".join(lines)

    # ── documents ────────────────────────────────────────────────────────────

    def document_prompt(
        self, document_type: str, profile: ProfileInput, opportunity: OpportunityInput, today: date
    ) -> Prompt:
        spec = self.document_type(document_type)
        if not spec.generatable or spec.prompt is None:
            raise ValueError(f"{document_type} is not written by the model")
        person = {"name": profile.name, "summary": profile.summary, **profile.attributes}
        tone = (
            f"\nThe applicant asks for this tone and style: {profile.tone_instructions.strip()}\n"
            if profile.tone_instructions.strip()
            else ""
        )
        text = fill(
            self.prompt_template(spec.prompt),
            today=f"{today.day} {today:%B %Y}",
            opportunity=self.opportunity_block(opportunity, DESCRIPTION_LIMIT),
            issuer=str(opportunity.attributes.get(self.issuer_field) or opportunity.issuer_name),
            profile=as_json(person),
            tone=tone,
        )
        return Prompt(text=text, purpose=WRITING)

    def score_prompt(self, profile: ProfileInput, opportunity: OpportunityInput) -> Prompt:
        person = {"name": profile.name, "summary": profile.summary, **profile.attributes}
        text = fill(
            self.prompt_template("score.md"),
            noun=self.noun["en"],
            opportunity=self.opportunity_block(opportunity, SCORE_LIMIT),
            profile=as_json(person),
        )
        return Prompt(text=text, purpose=SCORE)

    # ── reading a notice ─────────────────────────────────────────────────────

    def from_json_ld(self, node: dict[str, Any], page_url: str) -> Extracted | None:
        return None  # schema.org has no type for these notices: the model reads them

    def extraction_schema(self) -> dict[str, Any]:
        props: dict[str, Any] = {}
        for key, prop in self._properties().items():
            if prop.get("type") == "string" or "enum" in prop:
                props[key] = {"type": "string", **({"enum": prop["enum"]} if "enum" in prop else {})}
        return {"type": "object", "properties": props, "required": list(props)}

    def extraction_prompt(self, text: str) -> Prompt:
        fields = []
        for key, prop in self.extraction_schema()["properties"].items():
            label = self._properties()[key].get("x-label", {}).get("en", key)
            choice = f" (one of: {', '.join(repr(v) for v in prop['enum'] if v)})" if "enum" in prop else ""
            fields.append(f"- {key}: {label}{choice}")
        body = fill(self.prompt_template("extract.md"), noun=self.noun["en"], fields="\n".join(fields), text=text)
        return Prompt(text=body, purpose=GENERAL)

    def from_extraction(self, data: dict[str, Any]) -> Extracted:
        values: dict[str, Any] = {}
        for key, prop in self.extraction_schema()["properties"].items():
            value = str(data.get(key) or "").strip()
            if "enum" in prop and value not in prop["enum"]:
                value = ""
            limit = self._properties()[key].get("maxLength")
            values[key] = value[:limit] if limit else value
        attributes = self.opportunity_model(**values).model_dump()
        return Extracted(
            title=str(values.get(self.title_field, ""))[:500],
            issuer_name=str(values.get(self.issuer_field, ""))[:300],
            attributes=attributes,
        )

    # ── discovery ────────────────────────────────────────────────────────────

    def searchable(self, title: str, attributes: dict[str, Any]) -> Searchable:
        location = str(attributes.get(self.location_field) or "") if self.location_field else ""
        remote = bool(self.remote_field and attributes.get(self.remote_field) == "remote")
        return Searchable(
            title=str(attributes.get(self.title_field) or title),
            body=str(attributes.get(self.description_field) or ""),
            location=location,
            remote=remote or "remote" in location.lower(),
            sponsorship="",
        )

    def dedupe_key(self, issuer_name: str, title: str, attributes: dict[str, Any]) -> str:
        """Issuer and title, and the notice's own reference where it has one."""
        reference = str(attributes.get(self.reference_field) or "") if self.reference_field else ""
        parts = [
            normalise(str(issuer_name or attributes.get(self.issuer_field) or "")),
            normalise(str(attributes.get(self.title_field) or title)),
            normalise(reference),
        ]
        return "|".join(parts)[:500]
