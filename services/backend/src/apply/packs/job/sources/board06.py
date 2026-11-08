"""board06's public jobs widget API: apply.workable.com/api/v1/widget/accounts/{account} (made for career pages)."""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import attributes, markdown, text, when, workplace


class Board06Source(SourceAdapter):
    kind = "board06"
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
    addresses = (re.compile(r"^https?://apply\.workable\.com/(?P<account>[\w-]+)"),)
    default_base_url = "https://apply.workable.com"
    config_fields = (
        ConfigField(
            "account",
            en_ne("Account name", "खाताको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"board06: {config['account']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        data = await fetcher.fetch_json(f"{base_url}/api/v1/widget/accounts/{config['account']}?details=true")
        company = text(data.get("name")) or config["account"]
        listings = []
        for job in data.get("jobs") or []:
            title, shortcode = text(job.get("title")), text(job.get("shortcode"))
            url = text(job.get("shortlink")) or text(job.get("url"))
            if not title or not shortcode or not url:
                continue
            place = ", ".join(p for p in (text(job.get("city")), text(job.get("country"))) if p)
            remote = bool(job.get("telecommuting"))
            listings.append(
                Listing(
                    ref=shortcode,
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        description=markdown(text(job.get("description"))),
                        location=place or ("Remote" if remote else ""),
                        workplace_value=workplace(None, remote_hint=remote),
                        employment_type=text(job.get("employment_type")),
                    ),
                    source_url=url,
                    apply_url=text(job.get("application_url")) or url,
                    posted_at=when(job.get("published_on") or job.get("created_at")),
                )
            )
        return listings
