"""board01's Job Board API: boards-api.greenhouse.io/v1/boards/{board}/jobs (public, made for job sites)."""

import re
from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import attributes, markdown, text, when, workplace


class Board01Source(SourceAdapter):
    kind = "board01"
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
    addresses = (re.compile(r"^https?://(?:job-)?boards\.greenhouse\.io/(?P<board>[\w-]+)"),)
    default_base_url = "https://boards-api.greenhouse.io"
    config_fields = (
        ConfigField(
            "board",
            en_ne("Board name", "बोर्डको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
        ),
        ConfigField(
            "company",
            en_ne("Company name", "कम्पनीको नाम"),
            en_ne("As you'd like it shown. Empty: the board's own name.", "जसरी देखाउन चाहनुहुन्छ। खाली भए: बोर्डकै नाम।"),
            required=False,
            pattern=r"^.{1,120}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return config.get("company") or config["board"]

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        board = config["board"]
        company = config.get("company", "")
        if not company:
            info = await fetcher.fetch_json(f"{base_url}/v1/boards/{board}")
            company = text(info.get("name")) or board
        data = await fetcher.fetch_json(f"{base_url}/v1/boards/{board}/jobs?content=true")
        listings = []
        for job in data.get("jobs", []):
            title = text(job.get("title"))
            url = text(job.get("absolute_url"))
            if not title or not url:
                continue
            location = text((job.get("location") or {}).get("name"))
            listings.append(
                Listing(
                    ref=str(job.get("id")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        location=location,
                        description=markdown(text(job.get("content")), escaped=True),
                        workplace_value=workplace(None, remote_hint="remote" in location.lower()),
                    ),
                    source_url=url,
                    apply_url=url,
                    posted_at=when(job.get("first_published") or job.get("updated_at")),
                )
            )
        return listings
