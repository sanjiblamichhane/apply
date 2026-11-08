"""
A company's board04 careers site (…myworkdayjobs.com/<site>): the JSON its own pages read, under /wday/cxs/,
which its robots.txt allows. Asked at most every 12 hours, for the newest ``MAX_POSTINGS`` (each posting's
description is one more request), never signed in.
"""

import re
from typing import Any

from apply.i18n import label as en_ne
from apply.libs.extract import FetchError

from ...base import ConfigField, Listing, SourceAdapter
from .common import at, attributes, markdown, text, when, workplace

PAGE = 20  # the most a board04 site gives at once
MAX_POSTINGS = 60
SITE = re.compile(
    r"^https://(?P<host>(?P<tenant>[a-z0-9-]+)\.wd\d{1,3}\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?"
    r"(?P<site>[A-Za-z0-9_-]{1,80})/?$"
)


def parse_site(url: str) -> tuple[str, str, str]:
    """(host, tenant, site) from a careers site's address."""
    found = SITE.match(url.strip())
    if not found:
        raise ValueError(f"not a board04 careers site: {url}")
    return found["host"], found["tenant"], found["site"]


class Board04Source(SourceAdapter):
    kind = "board04"
    label = en_ne("Company job board", "कम्पनीको जागिर बोर्ड")
    description = en_ne(
        "A company's own job board, recognised from its address.",
        "कुनै कम्पनीको आफ्नै जागिर बोर्ड, ठेगानाबाट चिनिन्छ।",
    )
    terms = en_ne(
        "The company's own careers site, read as its pages read it: at most every 12 hours, the newest 60 postings.",
        "कम्पनीकै क्यारियर साइट, यसका पेजले पढे जसरी: बढीमा १२ घण्टामा एक पटक, सबैभन्दा नयाँ ६० पोस्टिङ।",
    )
    min_interval_hours = 12.0
    addresses = (re.compile(r"^(?P<careers_url>https://[\w-]+\.(?:wd\d+\.)?myworkday(?:jobs|site)\.com/[^?#\s]+)"),)
    default_base_url = "https://{host}"
    config_fields = (
        ConfigField(
            "careers_url",
            en_ne("Careers site address", "क्यारियर साइटको ठेगाना"),
            en_ne("As it opens in your browser.", "ब्राउजरमा खुल्ने जस्तै।"),
            pattern=SITE.pattern,
        ),
        ConfigField(
            "company",
            en_ne("Company name", "कम्पनीको नाम"),
            en_ne("As you'd like it shown. Empty: from the address.", "जसरी देखाउन चाहनुहुन्छ। खाली भए: ठेगानाबाट।"),
            required=False,
            pattern=r"^.{1,120}$",
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
        return config.get("company") or f"board04: {parse_site(config['careers_url'])[1]}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        host, tenant, site = parse_site(config["careers_url"])
        api = f"{at(base_url, host=host)}/wday/cxs/{tenant}/{site}"
        public = f"https://{host}/{site}"
        company = config.get("company") or tenant.replace("-", " ").title()
        postings: list[dict[str, Any]] = []
        while len(postings) < MAX_POSTINGS:
            page = await fetcher.post_json(
                f"{api}/jobs",
                {"applyFacets": {}, "limit": PAGE, "offset": len(postings), "searchText": config.get("search", "")},
            )
            batch = page.get("jobPostings") or []
            postings.extend(batch)
            if len(batch) < PAGE or len(postings) >= int(page.get("total") or 0):
                break
        listings = []
        for posting in postings[:MAX_POSTINGS]:
            path, title = text(posting.get("externalPath")), text(posting.get("title"))
            if not path.startswith("/job/") or not title:
                continue
            try:
                info = (await fetcher.fetch_json(f"{api}{path}")).get("jobPostingInfo") or {}
            except FetchError:
                info = {}
            location = text(info.get("location")) or text(posting.get("locationsText"))
            url = text(info.get("externalUrl")) or f"{public}{path}"
            listings.append(
                Listing(
                    ref=text(info.get("jobReqId")) or path,
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        description=markdown(text(info.get("jobDescription"))),
                        location=location,
                        workplace_value=workplace(info.get("remoteType"), remote_hint="remote" in location.lower()),
                        employment_type=text(info.get("timeType")),
                    ),
                    source_url=url,
                    apply_url=f"{url.rstrip('/')}/apply",
                    posted_at=when(info.get("startDate")),
                )
            )
        return listings
