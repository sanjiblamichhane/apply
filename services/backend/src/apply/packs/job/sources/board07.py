"""board07's public careers API: {company}.recruitee.com/api/offers/ (what its career sites are built on)."""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import at, attributes, markdown, salary, text, when


class Board07Source(SourceAdapter):
    kind = "board07"
    label = en_ne("Company job board", "कम्पनीको जागिर बोर्ड")
    description = en_ne(
        "A company's own job board, recognised from its address.",
        "कुनै कम्पनीको आफ्नै जागिर बोर्ड, ठेगानाबाट चिनिन्छ।",
    )
    terms = en_ne(
        "Its public listings API, asked at most every 6 hours.",
        "यसको सार्वजनिक सूची API, बढीमा ६ घण्टामा एक पटक सोधिन्छ।",
    )
    min_interval_hours = 6.0
    addresses = (re.compile(r"^https?://(?P<company>[a-z0-9-]+)\.recruitee\.com"),)
    default_base_url = "https://{company}.recruitee.com"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company name in the address", "ठेगानामा कम्पनीको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
            pattern=r"^[a-z0-9-]{1,63}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"board07: {config['company']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        data = await fetcher.fetch_json(f"{at(base_url, company=config['company'])}/api/offers/")
        listings = []
        for offer in data.get("offers") or []:
            title, url = text(offer.get("title")), text(offer.get("careers_url"))
            if not title or not url or text(offer.get("status")) not in ("", "published"):
                continue
            company = text(offer.get("company_name")) or config["company"]
            body = "\n\n".join(
                markdown(text(offer.get(part))) for part in ("description", "requirements") if offer.get(part)
            )
            pay = offer.get("salary") or {}
            mode = (
                "remote"
                if offer.get("remote")
                else "hybrid"
                if offer.get("hybrid")
                else ("onsite" if offer.get("on_site") else "")
            )
            listings.append(
                Listing(
                    ref=text(offer.get("id")) or text(offer.get("slug")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        description=body,
                        location=text(offer.get("location")),
                        workplace_value=mode,
                        employment_type=text(offer.get("employment_type_code")).replace("_", " "),
                        salary=salary(pay.get("min"), pay.get("max"), pay.get("currency"), pay.get("period")),
                    ),
                    source_url=url,
                    apply_url=text(offer.get("careers_apply_url")) or url,
                    posted_at=when(offer.get("published_at") or offer.get("created_at")),
                )
            )
        return listings
