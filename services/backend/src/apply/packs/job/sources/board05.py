"""
board05' public Posting API: api.smartrecruiters.com/v1/companies/{company}/postings, made for career
sites and job boards. The list has no descriptions, so each posting is asked for once more (at most
``MAX_POSTINGS`` a time), at most every 6 hours.
"""

import re
from typing import Any
from urllib.parse import quote

from apply.i18n import label as en_ne
from apply.libs.extract import FetchError

from ...base import ConfigField, Listing, SourceAdapter
from .common import attributes, markdown, text, when

MAX_POSTINGS = 50
SECTIONS = ("jobDescription", "qualifications", "additionalInformation")


class Board05Source(SourceAdapter):
    kind = "board05"
    label = en_ne("Company job board", "कम्पनीको जागिर बोर्ड")
    description = en_ne(
        "A company's own job board, recognised from its address.",
        "कुनै कम्पनीको आफ्नै जागिर बोर्ड, ठेगानाबाट चिनिन्छ।",
    )
    terms = en_ne(
        "Its public listings API, asked at most every 6 hours, for up to 50 postings.",
        "यसको सार्वजनिक सूची API, बढीमा ६ घण्टामा एक पटक, ५० वटासम्म पोस्टिङका लागि सोधिन्छ।",
    )
    min_interval_hours = 6.0
    addresses = (re.compile(r"^https?://(?:jobs|careers)\.smartrecruiters\.com/(?P<company>[\w-]+)"),)
    default_base_url = "https://api.smartrecruiters.com"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company identifier", "कम्पनीको पहिचान"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
        ),
        ConfigField(
            "search",
            en_ne("Search words", "खोज शब्दहरू"),
            en_ne("Optional, for example: data engineer.", "ऐच्छिक, जस्तै: data engineer।"),
            required=False,
            pattern=r"^[\w .+#-]{1,80}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"board05: {config['company']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        company = config["company"]
        search = f"&q={quote(config['search'])}" if config.get("search") else ""
        found = await fetcher.fetch_json(f"{base_url}/v1/companies/{company}/postings?limit=100{search}")
        listings = []
        for posting in (found.get("content") or [])[:MAX_POSTINGS]:
            posting_id, title = text(posting.get("id")), text(posting.get("name"))
            if not posting_id or not title:
                continue
            try:
                detail = await fetcher.fetch_json(f"{base_url}/v1/companies/{company}/postings/{posting_id}")
            except FetchError:
                detail = {}  # listed without its description rather than not at all
            sections = ((detail.get("jobAd") or {}).get("sections")) or {}
            parts = [sections.get(key) or {} for key in SECTIONS]
            description = "\n\n".join(
                f"### {text(part.get('title'))}\n\n{markdown(text(part.get('text')))}"
                if part.get("title")
                else markdown(text(part.get("text")))
                for part in parts
                if part.get("text")
            )
            location = posting.get("location") or {}
            place = text(location.get("fullLocation")) or ", ".join(
                p for p in (text(location.get("city")), text(location.get("country")).upper()) if p
            )
            mode = "remote" if location.get("remote") else "hybrid" if location.get("hybrid") else ""
            owner = text((posting.get("company") or {}).get("name")) or company
            url = text(detail.get("postingUrl")) or f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
            listings.append(
                Listing(
                    ref=posting_id,
                    title=title,
                    issuer_name=owner,
                    attributes=attributes(
                        title=title,
                        company=owner,
                        description=description,
                        location=place,
                        workplace_value=mode,
                        employment_type=text((posting.get("typeOfEmployment") or {}).get("label")),
                    ),
                    source_url=url,
                    apply_url=text(detail.get("applyUrl")) or url,
                    posted_at=when(posting.get("releasedDate")),
                )
            )
        return listings
