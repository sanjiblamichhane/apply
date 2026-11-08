"""The job pack: job openings, a person's work history, resumes and cover letters, the job-search pipeline."""

import calendar
import re
import unicodedata
from datetime import UTC, date, datetime, time
from typing import Any

from apply.i18n import Label
from apply.i18n import label as en_ne
from apply.libs.extract import text as ld_text
from apply.libs.extract import to_markdown
from apply.libs.llm import GENERAL, SCORE, WRITING

from ..base import (
    COPY_TABS,
    CopyGroup,
    CopyItem,
    CopyTab,
    DocumentTypeSpec,
    Extracted,
    OpportunityInput,
    Pack,
    PipelineSpec,
    ProfileInput,
    Prompt,
    Searchable,
    StageSpec,
    as_json,
    fill,
)
from .questions import QUESTIONS
from .schemas import Experience, JobOpportunity, JobProfile
from .sources import SOURCES

DESCRIPTION_LIMIT = 24_000  # characters of a posting given to the writer; fits num_ctx 16384 with a profile
SCORE_DESCRIPTION_LIMIT = 12_000  # scoring needs the requirements, not every perk: quicker, and the same answer

PIPELINE = PipelineSpec(
    key="job",
    label=en_ne("Job search", "जागिर खोजी"),
    stages=(
        StageSpec("new", en_ne("New", "नयाँ"), "active"),
        StageSpec("in_progress", en_ne("In progress", "प्रगतिमा"), "active", follow_up_after_days=7),
        StageSpec("blocked", en_ne("Blocked", "अड्किएको"), "paused"),
        StageSpec(
            "screening", en_ne("Initial screening", "प्रारम्भिक छनोट"), "active", "interview", expected_duration_days=7
        ),
        StageSpec("interview", en_ne("Interview", "अन्तर्वार्ता"), "active", "interview", expected_duration_days=14),
        StageSpec("final_round", en_ne("Final round", "अन्तिम चरण"), "active", "interview", expected_duration_days=14),
        StageSpec("offer", en_ne("Offer", "प्रस्ताव"), "active", "negotiation", follow_up_after_days=2),
        StageSpec("declined", en_ne("Declined", "अस्वीकृत"), "failure", "decision", is_terminal=True),
        StageSpec("cancelled", en_ne("Cancelled", "रद्द"), "failure", "decision", is_terminal=True),
        StageSpec("accepted", en_ne("Accepted", "स्वीकृत"), "success", "decision", is_terminal=True),
    ),
)

DOCUMENT_TYPES = (
    DocumentTypeSpec(
        "resume",
        en_ne("Resume", "बायोडाटा"),
        en_ne(
            "A resume tailored to this job, from your profile.", "तपाईंको प्रोफाइलबाट यो जागिरका लागि मिलाइएको बायोडाटा।"
        ),
        generatable=True,
        prompt="resume.md",
    ),
    DocumentTypeSpec(
        "cover_letter",
        en_ne("Cover letter", "कभर लेटर"),
        en_ne(
            "A letter to the employer for this job, from your profile.",
            "तपाईंको प्रोफाइलबाट यो जागिरका लागि रोजगारदातालाई पत्र।",
        ),
        generatable=True,
        prompt="cover_letter.md",
        layout="letter",
    ),
    DocumentTypeSpec(
        "job_description",
        en_ne("Job description", "कामको विवरण"),
        en_ne("The posting as it was when you apply.", "आवेदन दिँदाको जागिर सूचना।"),
        generatable=False,
        accepts_upload=True,
    ),
)

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_title": {"type": "string"},
        "company_name": {"type": "string"},
        "description_markdown": {"type": "string"},
        "location": {"type": "string"},
        "workplace": {"type": "string", "enum": ["", "onsite", "hybrid", "remote"]},
        "employment_type": {"type": "string"},
        "salary_text": {"type": "string"},
        "visa_sponsorship_text": {"type": "string"},
        "hiring_manager": {"type": "string"},
    },
    "required": [
        "job_title",
        "company_name",
        "description_markdown",
        "location",
        "workplace",
        "employment_type",
        "salary_text",
        "visa_sponsorship_text",
        "hiring_manager",
    ],
}


COPY: dict[str, Label] = {
    "first_name": en_ne("First name", "पहिलो नाम"),
    "middle_name": en_ne("Middle name", "बीचको नाम"),
    "last_name": en_ne("Last name", "थर"),
    "phone_international": en_ne("Phone, international", "फोन, अन्तर्राष्ट्रिय"),
}
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def _field_label(name: str) -> Label:
    return _label_of(JobProfile, name)


def _name_parts(full_name: str) -> tuple[str, str, str]:
    """First, middle and last: "Sam Bahadur Rai" → Sam, Bahadur, Rai; one word is only a first name."""
    words = full_name.split()
    if len(words) < 2:
        return (words[0] if words else ""), "", ""
    return words[0], " ".join(words[1:-1]), words[-1]


def month_year(text: str) -> tuple[int, int] | None:
    """(year, month) from "Jan 2021", "January 2021", "2021-01", "01/2021", "1/2021" or a whole date "2021-01-15";
    None otherwise."""
    t = text.strip().lower()
    if m := re.fullmatch(r"([a-z]{3})[a-z]*\.?,?\s+(\d{4})", t):
        return (int(m[2]), MONTHS.index(m[1]) + 1) if m[1] in MONTHS else None
    if (m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)) and _whole_date(t):
        year, month = int(m[1]), int(m[2])
    elif m := re.fullmatch(r"(\d{4})-(\d{1,2})", t):
        year, month = int(m[1]), int(m[2])
    elif m := re.fullmatch(r"(\d{1,2})/(\d{4})", t):
        year, month = int(m[2]), int(m[1])
    else:
        return None
    return (year, month) if 1 <= month <= 12 else None


START_DAY = 15  # a job's start with only a month: the middle of it
END_DAY = 30  # its end: the 30th, or February's last day


def _whole_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def with_day(text: str, *, end: bool) -> str:
    """
    A job's month as a whole date (YYYY-MM-DD), for forms that ask for a day: "Jan 2021" → 2021-01-15 as a start,
    2021-01-30 as an end (February: its last day). Anything else (a year alone, "Present", a whole date) as it is.
    """
    found = None if _whole_date(text) else month_year(text)
    if not found:
        return text
    year, month = found
    day = min(END_DAY, calendar.monthrange(year, month)[1]) if end else START_DAY
    return date(year, month, day).isoformat()


def as_written(text: str) -> str:
    """A whole date as the month a resume shows ("2021-01-15" → "Jan 2021"): the day is often only a default."""
    when = _whole_date(text)
    return f"{when:%b %Y}" if when else text


def _dates(attributes: dict[str, Any], change: Any) -> dict[str, Any]:
    """The profile with each job's From and Until passed through ``change(text, end=...)``."""
    jobs = attributes.get("experience")
    if not isinstance(jobs, list):
        return attributes
    moved = [
        {
            **job,
            **{key: change(job[key], end=key == "end") for key in ("start", "end") if isinstance(job.get(key), str)},
        }
        if isinstance(job, dict)
        else job
        for job in jobs
    ]
    return {**attributes, "experience": moved}


def _with_date_forms(group: CopyGroup) -> CopyGroup:
    """A job's From and Until, each followed by the same month as MM/YYYY and YYYY-MM (what forms ask for)."""
    dated = [_label_of(Experience, "start"), _label_of(Experience, "end")]
    items: list[CopyItem] = []
    for item in group.items:
        items.append(item)
        found = month_year(item.value) if item.label in dated else None
        if not found:
            continue
        year, month = found
        forms = [(f"{month:02d}/{year}", "MM/YYYY"), (f"{year}-{month:02d}", "YYYY-MM")]
        if whole := _whole_date(item.value):
            forms.insert(0, (f"{whole:%m/%d/%Y}", "MM/DD/YYYY"))
        for shown, pattern in forms:
            if shown != item.value:
                items.append(CopyItem({lang: f"{text} ({pattern})" for lang, text in item.label.items()}, shown))
    return CopyGroup(group.title, items)


def _label_of(model: Any, name: str) -> Label:
    extra = model.model_fields[name].json_schema_extra
    return extra["x-label"] if isinstance(extra, dict) else {"en": name}


class JobPack(Pack):
    key = "job"
    version = "1"
    label = en_ne("Jobs", "जागिर")
    description = en_ne("Job openings posted by employers.", "रोजगारदाताले राखेका जागिरका अवसरहरू।")
    profile_kinds = ("individual",)
    profile_model = JobProfile
    opportunity_model = JobOpportunity
    document_types = DOCUMENT_TYPES
    pipeline = PIPELINE
    json_ld_types = frozenset({"JobPosting"})
    prompts_package = "apply.packs.job.prompts"
    profile_document = "resume (CV)"
    sources = SOURCES
    standard_questions = QUESTIONS
    submitted_stage = "in_progress"
    search_options = frozenset({"locations", "remote_only", "needs_sponsorship"})
    auto = True

    def person_name(self, profile: ProfileInput) -> str:
        return str(profile.attributes.get("full_name") or "").strip()

    def letterhead(self, profile: ProfileInput) -> tuple[str, str]:
        """The template's header line: "Place | Phone: … | Email: … | Profile: …", each part only if known."""
        values = self.form_values(profile)
        name = values.get("full_name") or profile.name.strip()
        if not name:
            return "", ""
        line = [_plain(values["location"])] if values.get("location") else []
        if values.get("phone"):
            digits = re.sub(r"[^\d+]", "", values["phone"])
            line.append(f"Phone: [{_plain(values['phone'])}](tel:{digits})" if len(digits) >= 3 else "")
        if values.get("email") and "@" in values["email"] and " " not in values["email"]:
            line.append(f"Email: [{_plain(values['email'])}](mailto:{values['email']})")
        linkedin = values.get("linkedin", "")
        if linkedin.startswith(("https://", "http://")) and " " not in linkedin:
            shown = re.sub(r"^https?://(www\.)?", "", linkedin).rstrip("/")
            line.append(f"Profile: [{_plain(shown)}]({linkedin})")
        return _plain(name), " | ".join(x for x in line if x)

    def copy_sheet(self, profile: ProfileInput) -> list[CopyTab]:
        """Basics as forms ask for them (the name in parts, the address, the phone with its country code), and
        each job's dates also as MM/YYYY and YYYY-MM (and MM/DD/YYYY when there's a day)."""
        attrs = profile.attributes
        values = self.form_values(profile)
        basics: list[CopyItem] = []

        def add(item_label: Label, value: str) -> None:
            if value.strip():
                basics.append(CopyItem(item_label, value.strip()))

        add(_field_label("full_name"), values.get("full_name", ""))
        first, middle, last = _name_parts(values.get("full_name", ""))
        add(COPY["first_name"], first)
        add(COPY["middle_name"], middle)
        add(COPY["last_name"], last)
        add(_field_label("email"), values.get("email", ""))
        phone = str(attrs.get("phone") or "").strip()
        add(_field_label("phone"), phone)
        code = str(attrs.get("phone_country_code") or "").strip()
        if phone and code and not phone.startswith("+"):
            add(COPY["phone_international"], f"{code if code.startswith('+') else '+' + code} {phone.lstrip('0')}")
        add(_field_label("phone_country_code"), code)
        for key in ("location", "address_line1", "address_line2", "city", "region", "postal_code", "country"):
            add(_field_label(key), str(attrs.get(key) or ""))
        for link in attrs.get("links") or []:
            url = str(link.get("url") or "").strip()
            name = str(link.get("label") or "").strip()
            add({"en": name} if name else _field_label("links"), url)

        tabs = [t for t in super().copy_sheet(profile) if t.key not in ("basics", "links")]
        for tab in tabs:
            if tab.key == "experience":
                tab.groups[:] = [_with_date_forms(g) for g in tab.groups]
            if tab.key == "more":
                right = str(attrs.get("work_authorization") or "").strip()
                if right:
                    tab.groups[0].items.append(CopyItem(_field_label("work_authorization"), right))
        return ([CopyTab("basics", COPY_TABS["basics"], [CopyGroup("", basics)])] if basics else []) + tabs

    def form_values(self, profile: ProfileInput) -> dict[str, str]:
        attrs = profile.attributes
        full_name = str(attrs.get("full_name") or "").strip()
        first, _, last = full_name.partition(" ")
        values = {
            "full_name": full_name,
            "first_name": first,
            "last_name": last.strip(),
            "email": str(attrs.get("email") or ""),
            "phone": str(attrs.get("phone") or ""),
            "phone_country_code": str(attrs.get("phone_country_code") or ""),
            "location": str(attrs.get("location") or ""),
            "address_line1": str(attrs.get("address_line1") or ""),
            "address_line2": str(attrs.get("address_line2") or ""),
            "city": str(attrs.get("city") or ""),
            "region": str(attrs.get("region") or ""),
            "postal_code": str(attrs.get("postal_code") or ""),
            "country": str(attrs.get("country") or ""),
        }
        if not values["location"]:  # "Where you live", else the address's city and region
            values["location"] = ", ".join(v for v in (values["city"], values["region"]) if v.strip())
        for link in attrs.get("links") or []:
            url, label = str(link.get("url") or ""), str(link.get("label") or "").lower()
            key = (
                "linkedin"
                if "linkedin." in url or label == "linkedin"
                else "github"
                if "github." in url or label == "github"
                else "website"
            )
            if url and not values.get(key):  # the first of each kind
                values[key] = url
        experience = [e for e in attrs.get("experience") or [] if isinstance(e, dict)]
        current = next((e for e in experience if not e.get("end")), experience[0] if experience else None)
        if current:
            values["current_company"] = str(current.get("organisation") or "")
            values["current_title"] = str(current.get("title") or "")
        # Every employer in the profile, one per line: "Have you ever worked for …?" is answered from these.
        employers = dict.fromkeys(str(e.get("organisation") or "").strip() for e in experience)
        values["past_employers"] = "\n".join(e for e in employers if e)
        return {k: v.strip() for k, v in values.items() if v and v.strip()}

    def from_reading(self, data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """As read, with each job's month given a day (the 15th to start, the 30th to end): forms ask for one."""
        summary, attributes = super().from_reading(data)
        return summary, _dates(attributes, with_day)

    def describe(self, attributes: dict[str, Any]) -> tuple[str, str]:
        return str(attributes.get("job_title") or ""), str(attributes.get("company_name") or "")

    # ── documents ────────────────────────────────────────────────────────────

    def document_prompt(
        self, document_type: str, profile: ProfileInput, opportunity: OpportunityInput, today: date
    ) -> Prompt:
        spec = self.document_type(document_type)
        if not spec.generatable or spec.prompt is None:
            raise ValueError(f"{document_type} is not written by the model")
        attrs = opportunity.attributes
        description = attrs.get("description_markdown") or opportunity.source_text
        person = {
            "name": profile.name,
            "summary": profile.summary,
            **_dates(profile.attributes, lambda t, end: as_written(t)),
        }
        tone = (
            f"\nThe person asks for this tone and style: {profile.tone_instructions.strip()}\n"
            if profile.tone_instructions.strip()
            else ""
        )
        text = fill(
            self.prompt_template(spec.prompt),
            today=f"{today.day} {today:%B %Y}",
            job_title=attrs.get("job_title") or opportunity.title,
            company_name=attrs.get("company_name") or opportunity.issuer_name,
            location=attrs.get("location") or "",
            hiring_manager=attrs.get("hiring_manager") or "Hiring Manager",
            job_description=str(description)[:DESCRIPTION_LIMIT],
            profile=as_json(person),
            tone=tone,
        )
        return Prompt(text=text, purpose=WRITING)

    # ── discovery ────────────────────────────────────────────────────────────

    def searchable(self, title: str, attributes: dict[str, Any]) -> Searchable:
        location = str(attributes.get("location") or "")
        return Searchable(
            title=str(attributes.get("job_title") or title),
            body=str(attributes.get("description_markdown") or ""),
            location=location,
            remote=attributes.get("workplace") == "remote" or "remote" in location.lower(),
            sponsorship=str(attributes.get("visa_sponsorship_text") or ""),
        )

    def dedupe_key(self, issuer_name: str, title: str, attributes: dict[str, Any]) -> str:
        """
        Issuer, title and place, normalised. Remote postings are just "remote": boards word the same remote job
        differently ("Remote - US", "Remote (USA)"); the same title in two cities stays two jobs.
        """
        location = _normalise(str(attributes.get("location") or ""))
        if attributes.get("workplace") == "remote" or "remote" in location.split():
            location = "remote"
        parts = [
            _normalise(str(issuer_name or attributes.get("company_name") or "")),
            _normalise(str(attributes.get("job_title") or title)),
            location,
        ]
        return "|".join(parts)[:500]

    def score_prompt(self, profile: ProfileInput, opportunity: OpportunityInput) -> Prompt:
        attrs = opportunity.attributes
        person = {"name": profile.name, "summary": profile.summary, **profile.attributes}
        text = fill(
            self.prompt_template("score.md"),
            job_title=attrs.get("job_title") or opportunity.title,
            company_name=attrs.get("company_name") or opportunity.issuer_name,
            location=attrs.get("location") or "",
            workplace=attrs.get("workplace") or "",
            sponsorship=attrs.get("visa_sponsorship_text") or "",
            job_description=str(attrs.get("description_markdown") or opportunity.source_text)[:SCORE_DESCRIPTION_LIMIT],
            profile=as_json(person),
        )
        return Prompt(text=text, purpose=SCORE)

    # ── reading a posting ────────────────────────────────────────────────────

    def from_json_ld(self, node: dict[str, Any], page_url: str) -> Extracted | None:
        title = ld_text(node.get("title"))
        if not title:
            return None
        company = ld_text(node.get("hiringOrganization"))
        attributes = JobOpportunity(
            job_title=title[:300],
            company_name=company[:300],
            description_markdown=to_markdown(str(node.get("description") or ""))[:100_000],
            location=_location(node)[:300],
            workplace=_workplace(node),
            employment_type=_employment_type(node)[:300],
            salary_text=_salary(node)[:300],
        ).model_dump()
        apply_url = ld_text(node.get("url")) or page_url
        return Extracted(
            title=title[:500],
            issuer_name=company[:300],
            attributes=attributes,
            apply_url=apply_url if apply_url.startswith(("http://", "https://")) else page_url,
            deadline=_deadline(node.get("validThrough")),
        )

    def extraction_prompt(self, text: str) -> Prompt:
        return Prompt(text=fill(self.prompt_template("extract.md"), text=text), purpose=GENERAL)

    def extraction_schema(self) -> dict[str, Any]:
        return EXTRACTION_SCHEMA

    def from_extraction(self, data: dict[str, Any]) -> Extracted:
        values = {key: str(data.get(key) or "").strip() for key in EXTRACTION_SCHEMA["properties"]}
        if values["workplace"] not in ("", "onsite", "hybrid", "remote"):
            values["workplace"] = ""
        for key, limit in (("description_markdown", 100_000), ("visa_sponsorship_text", 2000)):
            values[key] = values[key][:limit]
        for key in values:
            if key not in ("description_markdown", "visa_sponsorship_text"):
                values[key] = values[key][:300]
        attributes = JobOpportunity(**values).model_dump()
        return Extracted(title=values["job_title"], issuer_name=values["company_name"], attributes=attributes)


def _normalise(text: str) -> str:
    """Lower case, no accents, no punctuation, single spaces; "Sr." and "Senior" alike."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    plain = re.sub(r"\b(sr)\b\.?", "senior", plain)
    plain = re.sub(r"\b(jr)\b\.?", "junior", plain)
    plain = re.sub(r"\b(inc|ltd|llc|gmbh|pvt|plc|co)\b\.?", "", plain)
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


# ── JobPosting fields ────────────────────────────────────────────────────────


def _location(node: dict[str, Any]) -> str:
    places = node.get("jobLocation")
    places = places if isinstance(places, list) else [places] if places else []
    found: list[str] = []
    for place in places:
        address = place.get("address") if isinstance(place, dict) else None
        if isinstance(address, str):
            found.append(address.strip())
        elif isinstance(address, dict):
            parts = [ld_text(address.get(k)) for k in ("addressLocality", "addressRegion", "addressCountry")]
            joined = ", ".join(p for p in parts if p)
            if joined:
                found.append(joined)
    if not found and _workplace(node) == "remote":
        requirements = ld_text(node.get("applicantLocationRequirements"))
        return f"Remote ({requirements})" if requirements else "Remote"
    return "; ".join(dict.fromkeys(found))


def _workplace(node: dict[str, Any]) -> str:
    kind = ld_text(node.get("jobLocationType")).upper()
    return "remote" if "TELECOMMUTE" in kind else ""


def _employment_type(node: dict[str, Any]) -> str:
    raw = node.get("employmentType")
    values = raw if isinstance(raw, list) else [raw] if raw else []
    return ", ".join(str(v).replace("_", " ").capitalize() for v in values if v)


def _salary(node: dict[str, Any]) -> str:
    salary = node.get("baseSalary")
    if not isinstance(salary, dict):
        return ld_text(salary) if isinstance(salary, (int, float, str)) else ""
    currency = ld_text(salary.get("currency"))
    value = salary.get("value")
    unit = ""
    if isinstance(value, dict):
        unit = ld_text(value.get("unitText")).lower()
        low, high, exact = value.get("minValue"), value.get("maxValue"), value.get("value")
    else:
        low = high = None
        exact = value

    def money(amount: Any) -> str:
        try:
            number = float(amount)
        except (TypeError, ValueError):
            return str(amount)
        return f"{number:,.0f}" if number == int(number) else f"{number:,.2f}"

    if low and high:
        amount = f"{money(low)} – {money(high)}"
    elif low or high or exact:
        amount = money(low or high or exact)
    else:
        return ""
    per = {"year": " a year", "month": " a month", "week": " a week", "day": " a day", "hour": " an hour"}.get(unit, "")
    return f"{currency} {amount}{per}".strip()


def _deadline(value: Any) -> datetime | None:
    raw = ld_text(value)
    if not raw:
        return None
    if len(raw) == 10:  # a date alone: open until the end of that day
        try:
            return datetime.combine(date.fromisoformat(raw), time(23, 59), tzinfo=UTC)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(raw[:10]), time(23, 59))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _plain(text: str) -> str:
    """Words for markdown: nothing in them read as a link, emphasis or a line of its own."""
    return re.sub(r"[\[\]*_`#|\n]", " ", text).strip()
