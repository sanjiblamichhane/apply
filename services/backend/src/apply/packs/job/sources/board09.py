"""
board09's public positions feed: {company}.breezy.hr/json (what its career pages list). It has no
descriptions: tracking a posting reads its page.
"""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import at, attributes, text, when, workplace


class Board09Source(SourceAdapter):
    kind = "board09"
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
    addresses = (re.compile(r"^https?://(?P<company>[a-z0-9-]+)\.breezy\.hr"),)
    default_base_url = "https://{company}.breezy.hr"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company name in the address", "ठेगानामा कम्पनीको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
            pattern=r"^[a-z0-9-]{1,63}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"board09: {config['company']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        data = await fetcher.fetch_json(f"{at(base_url, company=config['company'])}/json")
        listings = []
        for position in data if isinstance(data, list) else []:
            title, url = text(position.get("name")), text(position.get("url"))
            if not title or not url:
                continue
            company = text((position.get("company") or {}).get("name")) or config["company"]
            location = position.get("location") or {}
            listings.append(
                Listing(
                    ref=text(position.get("id")) or text(position.get("friendly_id")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        description="",
                        location=text(location.get("name")),
                        workplace_value=workplace(None, remote_hint=bool(location.get("is_remote"))),
                        employment_type=text((position.get("type") or {}).get("name")),
                        salary=text(position.get("salary")),
                    ),
                    source_url=url,
                    apply_url=f"{url.rstrip('/')}/apply",
                    posted_at=when(position.get("published_date")),
                )
            )
        return listings
