"""What the job adapters share: turning a board's fields into the job pack's."""

import html
from datetime import UTC, datetime
from typing import Any

from apply.libs.extract import to_markdown

from ..schemas import JobOpportunity


def text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def markdown(raw_html: str, *, escaped: bool = False) -> str:
    """A board's HTML description as markdown (board01 escapes its HTML once more)."""
    source = html.unescape(raw_html) if escaped else raw_html
    return to_markdown(source)[:100_000]


def when(value: Any) -> datetime | None:
    """An ISO date ("…Z", or "… UTC" as board07 writes it), or milliseconds since 1970 (board02)."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    raw = str(value).strip()
    if raw.endswith(" UTC"):
        raw = raw[:-4] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def at(base_url: str, **slots: str) -> str:
    """
    A source's address. Its default has slots ("https://{company}.recruitee.com"), filled from its config; a
    test's (one local site for every company) has none, so it's used as it is.
    """
    for key, value in slots.items():
        base_url = base_url.replace("{" + key + "}", value)
    return base_url.rstrip("/")


def salary(low: Any, high: Any, currency: Any = "", period: Any = "") -> str:
    """ "USD 90,000 – 120,000 a year", from what the board gives (any part may be missing)."""

    def number(value: Any) -> str:
        try:
            return f"{float(value):,.0f}" if value not in (None, "", 0) else ""
        except (TypeError, ValueError):
            return text(value)

    low_text, high_text = number(low), number(high)
    if not low_text and not high_text:
        return ""
    amount = " – ".join(v for v in (low_text, high_text) if v)
    per = {
        "year": "a year",
        "annual": "a year",
        "yearly": "a year",
        "month": "a month",
        "monthly": "a month",
        "hour": "an hour",
        "hourly": "an hour",
    }.get(text(period).lower(), text(period))
    return " ".join(v for v in (text(currency).upper(), amount, per) if v)


def workplace(value: Any, *, remote_hint: bool = False) -> str:
    word = text(value).lower().replace("-", "").replace("_", "").replace(" ", "")
    if word in ("remote", "telecommute") or remote_hint:
        return "remote"
    if word == "hybrid":
        return "hybrid"
    if word in ("onsite", "inoffice", "office"):
        return "onsite"
    return ""


def attributes(
    *,
    title: str,
    company: str,
    description: str,
    location: str,
    workplace_value: str = "",
    employment_type: str = "",
    salary: str = "",
) -> dict[str, Any]:
    return JobOpportunity(
        job_title=title[:300],
        company_name=company[:300],
        description_markdown=description[:100_000],
        location=location[:300],
        workplace=workplace_value,  # type: ignore[arg-type]
        employment_type=employment_type[:300],
        salary_text=salary[:300],
    ).model_dump()
