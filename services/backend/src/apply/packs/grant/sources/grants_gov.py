"""
Grants.gov's public REST API (api.grants.gov/v1/api/search2, and fetchOpportunity for the details): US federal
funding opportunities, public domain, no key. apply asks at most every 6 hours and reads the details of at most
the first 20 opportunities per fetch.
"""

from datetime import UTC, datetime
from typing import Any

from apply.i18n import label as en_ne
from apply.libs.extract import FetchError, to_markdown

from ...base import ConfigField, Listing, SourceAdapter
from ..schemas import GrantOpportunity

DETAILS = 20


def _text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _date(value: Any) -> datetime | None:
    """Grants.gov writes dates as MM/DD/YYYY (sometimes with a time after)."""
    word = _text(value).split(" ")[0]
    for pattern in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(word, pattern).replace(hour=23, minute=59, tzinfo=UTC)
        except ValueError:
            continue
    return None


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}" if _text(value) not in ("", "0", "none") else ""
    except ValueError:
        return _text(value)


class GrantsGovSource(SourceAdapter):
    kind = "grants_gov"
    label = en_ne("Grants.gov (US federal)", "Grants.gov (अमेरिकी संघीय)")
    description = en_ne(
        "US federal funding opportunities that are posted or forecast, by search words.",
        "पोस्ट गरिएका वा पूर्वानुमान गरिएका अमेरिकी संघीय अनुदान अवसरहरू, खोज शब्द अनुसार।",
    )
    terms = en_ne(
        "Grants.gov's public API: no key, public domain data. Asked at most every 6 hours.",
        "Grants.gov को सार्वजनिक API: कुञ्जी चाहिँदैन, सार्वजनिक डाटा। बढीमा ६ घण्टामा एक पटक सोधिन्छ।",
    )
    attribution = "Grants.gov"
    min_interval_hours = 6.0
    default_base_url = "https://api.grants.gov"
    config_fields = (
        ConfigField(
            "keyword",
            en_ne("Search words", "खोज शब्दहरू"),
            en_ne("For example: rural health, STEM education.", "जस्तै: rural health, STEM education।"),
            pattern=r"^[\w ,.+#&-]{1,120}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"Grants.gov: {config['keyword']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        data = await fetcher.post_json(
            f"{base_url}/v1/api/search2",
            {"keyword": config["keyword"], "oppStatuses": "forecasted|posted", "rows": 100},
        )
        hits = ((data or {}).get("data") or {}).get("oppHits") or []
        listings = []
        for i, hit in enumerate(hits):
            ref, title = _text(hit.get("id")), _text(hit.get("title"))
            if not ref or not title:
                continue
            synopsis: dict[str, Any] = {}
            if i < DETAILS:
                try:
                    detail = await fetcher.post_json(f"{base_url}/v1/api/fetchOpportunity", {"opportunityId": int(ref)})
                    synopsis = ((detail or {}).get("data") or {}).get("synopsis") or {}
                except (FetchError, ValueError):
                    synopsis = {}  # the listing is still worth having; its details can be pasted
            funder = _text(hit.get("agency") or hit.get("agencyName") or synopsis.get("agencyName"))
            closing = _date(hit.get("closeDate") or synopsis.get("responseDate"))
            description = to_markdown(_text(synopsis.get("synopsisDesc")))[:100_000]
            link = f"https://www.grants.gov/search-results-detail/{ref}"
            attributes = GrantOpportunity(
                title=title[:300],
                funder=funder[:300],
                number=_text(hit.get("number"))[:300],
                description_markdown=description,
                award_ceiling=_money(synopsis.get("awardCeiling"))[:300],
                award_floor=_money(synopsis.get("awardFloor"))[:300],
                closing_date=closing.date().isoformat() if closing else "",
                eligibility=to_markdown(_text(synopsis.get("applicantEligibilityDesc")))[:2000],
                assistance_listings=", ".join(_text(c) for c in hit.get("cfdaList") or [])[:300],
                contact=_text(synopsis.get("agencyContactEmail") or synopsis.get("agencyContactName"))[:2000],
            ).model_dump()
            listings.append(
                Listing(
                    ref=ref,
                    title=title[:500],
                    issuer_name=funder[:300],
                    attributes=attributes,
                    source_url=link,
                    apply_url=link,
                    posted_at=_date(hit.get("openDate")),
                    deadline=closing,
                    source_text=f"{title}\n{funder}\n{description}"[:40_000],
                )
            )
        return listings
