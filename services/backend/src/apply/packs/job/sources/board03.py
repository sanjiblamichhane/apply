"""board03's Posting API: api.ashbyhq.com/posting-api/job-board/{board} (public, made for job sites)."""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import attributes, markdown, text, when, workplace

EMPLOYMENT = {
    "FullTime": "Full time",
    "PartTime": "Part time",
    "Intern": "Internship",
    "Contract": "Contract",
    "Temporary": "Temporary",
}


class Board03Source(SourceAdapter):
    kind = "board03"
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
    addresses = (re.compile(r"^https?://jobs\.ashbyhq\.com/(?P<board>[\w.%-]+)"),)
    default_base_url = "https://api.ashbyhq.com"
    config_fields = (
        ConfigField(
            "board",
            en_ne("Board name", "बोर्डको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
        ),
        ConfigField(
            "company",
            en_ne("Company name", "कम्पनीको नाम"),
            en_ne("As you'd like it shown. Empty: the board name.", "जसरी देखाउन चाहनुहुन्छ। खाली भए: बोर्डको नाम।"),
            required=False,
            pattern=r"^.{1,120}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return config.get("company") or config["board"]

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        company = self.display_name(config)
        data = await fetcher.fetch_json(f"{base_url}/posting-api/job-board/{config['board']}?includeCompensation=true")
        listings = []
        for job in data.get("jobs", []):
            if job.get("isListed") is False:
                continue
            title = text(job.get("title"))
            url = text(job.get("jobUrl"))
            if not title or not url:
                continue
            pay = text((job.get("compensation") or {}).get("compensationTierSummary"))
            listings.append(
                Listing(
                    ref=text(job.get("id")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        location=text(job.get("location")),
                        description=markdown(text(job.get("descriptionHtml"))),
                        workplace_value=workplace(job.get("workplaceType"), remote_hint=bool(job.get("isRemote"))),
                        employment_type=EMPLOYMENT.get(text(job.get("employmentType")), ""),
                        salary=pay,
                    ),
                    source_url=url,
                    apply_url=text(job.get("applyUrl")) or url,
                    posted_at=when(job.get("publishedAt")),
                )
            )
        return listings
