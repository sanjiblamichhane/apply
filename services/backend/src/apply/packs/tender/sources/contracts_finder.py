"""
UK Contracts Finder's open OCDS search (www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search): public
sector tenders, published under the Open Government Licence v3.0, which asks for the attribution shown with the
source. No key is needed; apply asks at most every 6 hours, for open tenders published in the last 30 days.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from apply.i18n import label as en_ne
from apply.libs.extract import to_markdown

from ...base import ConfigField, Listing, SourceAdapter
from ..schemas import TenderOpportunity

PREFIX = "ocds-b5fd17-"


def _text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _when(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _money(value: dict[str, Any] | None) -> str:
    if not value or value.get("amount") in (None, ""):
        return ""
    symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(_text(value.get("currency")), "")
    amount = value["amount"]
    shown = f"{amount:,.0f}" if isinstance(amount, (int, float)) else _text(amount)
    return f"{symbol}{shown}" if symbol else f"{shown} {_text(value.get('currency'))}".strip()


def _place(release: dict[str, Any]) -> str:
    for party in release.get("parties") or []:
        if "buyer" in (party.get("roles") or []):
            address = party.get("address") or {}
            return ", ".join(_text(address.get(k)) for k in ("locality", "region", "countryName") if address.get(k))
    return ""


def _contact(release: dict[str, Any]) -> str:
    for party in release.get("parties") or []:
        if "buyer" in (party.get("roles") or []):
            point = party.get("contactPoint") or {}
            return " · ".join(_text(point.get(k)) for k in ("name", "email", "telephone") if point.get(k))
    return ""


class ContractsFinderSource(SourceAdapter):
    kind = "contracts_finder"
    label = en_ne("Contracts Finder (UK)", "Contracts Finder (बेलायत)")
    description = en_ne(
        "Open public sector tenders in the UK, from the government's Contracts Finder.",
        "बेलायतका खुला सार्वजनिक बोलपत्रहरू, सरकारको Contracts Finder बाट।",
    )
    terms = en_ne(
        "Open Government Licence v3.0: apply names the source and the licence. Asked at most every 6 hours.",
        "Open Government Licence v3.0: apply ले स्रोत र इजाजतपत्रको नाम देखाउँछ। बढीमा ६ घण्टामा एक पटक सोधिन्छ।",
    )
    attribution = "Contracts Finder, under the Open Government Licence v3.0"
    min_interval_hours = 6.0
    default_base_url = "https://www.contractsfinder.service.gov.uk"
    config_fields = (
        ConfigField(
            "keyword",
            en_ne("Words to keep", "राख्ने शब्दहरू"),
            en_ne(
                "Optional: only tenders mentioning one of these words (software, cleaning…).",
                "ऐच्छिक: यीमध्ये कुनै शब्द भएका बोलपत्र मात्र (software, cleaning…)।",
            ),
            required=False,
            pattern=r"^[\w ,.+#&-]{1,120}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"Contracts Finder: {config['keyword']}" if config.get("keyword") else "Contracts Finder"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        since = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        url = f"{base_url}/Published/Notices/OCDS/Search?publishedFrom={since}&stages=tender&limit=100"
        data = await fetcher.fetch_json(url)
        words = [w.strip().lower() for w in config.get("keyword", "").replace(",", " ").split() if w.strip()]
        listings = []
        for release in data.get("releases") or []:
            tender = release.get("tender") or {}
            title = _text(tender.get("title"))
            ocid = _text(release.get("ocid"))
            if not title or not ocid or _text(tender.get("status")) not in ("", "active", "planned"):
                continue
            description = to_markdown(_text(tender.get("description")))[:100_000]
            if words and not any(w in f"{title} {description}".lower() for w in words):
                continue
            buyer = _text((release.get("buyer") or {}).get("name"))
            notice = f"{base_url}/notice/{ocid.removeprefix(PREFIX)}"
            classification = tender.get("classification") or {}
            closing = _when((tender.get("tenderPeriod") or {}).get("endDate"))
            attributes = TenderOpportunity(
                title=title[:300],
                buyer=buyer[:300],
                reference=ocid[:300],
                description_markdown=description,
                estimated_value=_money(tender.get("value"))[:300],
                closing_date=closing.date().isoformat() if closing else "",
                procedure=_text(tender.get("procurementMethodDetails") or tender.get("procurementMethod"))[:300],
                classification=" ".join(
                    f"{_text(classification.get('scheme'))} {_text(classification.get('id'))}".split()
                )[:300],
                place_of_performance=_place(release)[:300],
                contact=_contact(release)[:2000],
            ).model_dump()
            listings.append(
                Listing(
                    ref=ocid,
                    title=title[:500],
                    issuer_name=buyer[:300],
                    attributes=attributes,
                    source_url=notice,
                    apply_url=notice,
                    posted_at=_when(release.get("date")),
                    deadline=closing,
                    source_text=f"{title}\n{buyer}\n{description}"[:40_000],
                )
            )
        return listings
