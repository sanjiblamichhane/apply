"""board02's Postings API: api.lever.co/v0/postings/{company}?mode=json (public, made for job sites)."""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import attributes, markdown, text, when, workplace


def _salary(job: dict[str, Any]) -> str:
    salary = job.get("salaryRange") or {}
    low, high, currency = salary.get("min"), salary.get("max"), text(salary.get("currency"))
    if not (low or high):
        return ""
    amount = f"{low:,} – {high:,}" if low and high else f"{low or high:,}"
    per = {"per-year-salary": " a year", "per-month-salary": " a month", "per-hour-wage": " an hour"}.get(
        text(salary.get("interval")), ""
    )
    return f"{currency} {amount}{per}".strip()


class Board02Source(SourceAdapter):
    kind = "board02"
    label = en_ne("Company job board", "कम्पनीको जागिर बोर्ड")
    description = en_ne(
        "A company's own job board, recognised from its address.",
        "कुनै कम्पनीको आफ्नै जागिर बोर्ड, ठेगानाबाट चिनिन्छ।",
    )
    terms = en_ne(
        "Its public listings API, asked at most hourly.",
        "यसको सार्वजनिक सूची API, बढीमा घण्टामा एक पटक सोधिन्छ।",
    )
    min_interval_hours = 1.0
    addresses = (re.compile(r"^https?://jobs\.lever\.co/(?P<company>[\w.-]+)"),)
    default_base_url = "https://api.lever.co"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company's board name", "कम्पनीको बोर्डको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
        ),
        ConfigField(
            "display",
            en_ne("Company name", "कम्पनीको नाम"),
            en_ne("As you'd like it shown. Empty: the board name.", "जसरी देखाउन चाहनुहुन्छ। खाली भए: बोर्डको नाम।"),
            required=False,
            pattern=r"^.{1,120}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return config.get("display") or config["company"]

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        company = self.display_name(config)
        data = await fetcher.fetch_json(f"{base_url}/v0/postings/{config['company']}?mode=json")
        listings = []
        for job in data if isinstance(data, list) else []:
            title = text(job.get("text"))
            url = text(job.get("hostedUrl"))
            if not title or not url:
                continue
            categories = job.get("categories") or {}
            parts = [markdown(text(job.get("description")))]
            for block in job.get("lists") or []:
                parts.append(
                    f"## {text(block.get('text'))}\n\n{markdown('<ul>' + text(block.get('content')) + '</ul>')}"
                )
            parts.append(markdown(text(job.get("additional"))))
            listings.append(
                Listing(
                    ref=text(job.get("id")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        location=text(categories.get("location")),
                        description="\n\n".join(p for p in parts if p),
                        workplace_value=workplace(job.get("workplaceType")),
                        employment_type=text(categories.get("commitment")),
                        salary=_salary(job),
                    ),
                    source_url=url,
                    apply_url=text(job.get("applyUrl")) or url,
                    posted_at=when(job.get("createdAt")),
                )
            )
        return listings
