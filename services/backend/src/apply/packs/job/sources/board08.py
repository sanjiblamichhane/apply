"""
board08's public job feed: {company}.jobs.personio.de/xml (its documented XML feed for career pages and job
boards), read with apply's guarded XML fetch (no DTD, no entities).
"""

import re
from typing import Any
from xml.etree.ElementTree import Element

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import at, attributes, markdown, text, when


def _text(node: Element, path: str) -> str:
    found = node.find(path)
    return text(found.text) if found is not None and found.text else ""


class Board08Source(SourceAdapter):
    kind = "board08"
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
    addresses = (re.compile(r"^https?://(?P<company>[a-z0-9-]+)\.jobs\.personio\.(?:de|com)"),)
    default_base_url = "https://{company}.jobs.personio.de"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company name in the address", "ठेगानामा कम्पनीको नाम"),
            en_ne("From the board's address: filled in when you paste it.", "बोर्डको ठेगानाबाट: ठेगाना टाँस्दा आफैँ भरिन्छ।"),
            pattern=r"^[a-z0-9-]{1,63}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"board08: {config['company']}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        company = config["company"]
        root = await fetcher.fetch_xml(f"{at(base_url, company=company)}/xml?language=en")
        listings = []
        for position in root.iter("position"):
            ref, title = _text(position, "id"), _text(position, "name")
            if not ref.isdigit() or not title:
                continue
            owner = _text(position, "subcompany") or company
            offices = [_text(position, "office")] + [text(o.text) for o in position.findall("additionalOffices/office")]
            sections = [
                f"### {_text(d, 'name')}\n\n{markdown(_text(d, 'value'))}"
                if _text(d, "name")
                else markdown(_text(d, "value"))
                for d in position.findall("jobDescriptions/jobDescription")
                if _text(d, "value")
            ]
            kind = " ".join(p for p in (_text(position, "schedule"), _text(position, "employmentType")) if p)
            url = f"https://{company}.jobs.personio.de/job/{ref}"
            listings.append(
                Listing(
                    ref=ref,
                    title=title,
                    issuer_name=owner,
                    attributes=attributes(
                        title=title,
                        company=owner,
                        description="\n\n".join(sections),
                        location=" · ".join(o for o in offices if o),
                        employment_type=kind.replace("-", " "),
                    ),
                    source_url=url,
                    apply_url=f"{url}#apply",
                    posted_at=when(_text(position, "createdAt")),
                )
            )
        return listings
