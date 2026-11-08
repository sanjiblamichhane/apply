#!/usr/bin/env python3
"""
Stubs for a new platform, then the few lines to add by hand. See CONTRIBUTING.md, "Adding a platform".

    tools/new-platform.py source board11 --name "board11" --url "https://{company}.teamtailor.com"
    tools/new-platform.py board  board11 --name "board11" --host "*.teamtailor.com"

A source: services/backend/src/apply/packs/job/sources/<key>.py, with every label's Nepali left empty (the
i18n test fails until it's written) and a fetch to finish. A board: its entry in boards.json (extension only:
"auto": false), and the defineBoard line to put in adapters/more.ts.

Standard library only; it never overwrites a file.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = '''"""
{name}'s public API: {url} (made for others to read; checked live on <date>). Asked at most every
{hours} hours.
"""

from typing import Any

from apply.i18n import label as en_ne

from ...base import ConfigField, Listing, SourceAdapter
from .common import at, attributes, markdown, text, when


class {cls}Source(SourceAdapter):
    kind = "{key}"
    label = en_ne("{name} company", "")
    description = en_ne("A company's open jobs on {name}.", "")
    terms = en_ne("{name}'s public API, asked at most every {hours} hours.", "")
    min_interval_hours = {hours}.0
    default_base_url = "{url}"
    config_fields = (
        ConfigField(
            "company",
            en_ne("Company name in the address", ""),
            en_ne("From the jobs page's address.", ""),
            pattern=r"^[a-z0-9-]{{1,63}}$",
        ),
    )

    def display_name(self, config: dict[str, str]) -> str:
        return f"{name}: {{config['company']}}"

    async def fetch(self, fetcher: Any, config: dict[str, str], base_url: str) -> list[Listing]:
        data = await fetcher.fetch_json(f"{{at(base_url, company=config['company'])}}/TODO")
        listings = []
        for job in data.get("jobs") or []:  # TODO: the platform's own field names
            title, url = text(job.get("title")), text(job.get("url"))
            if not title or not url:
                continue
            company = text(job.get("company")) or config["company"]
            listings.append(
                Listing(
                    ref=text(job.get("id")),
                    title=title,
                    issuer_name=company,
                    attributes=attributes(
                        title=title,
                        company=company,
                        description=markdown(text(job.get("description"))),
                        location=text(job.get("location")),
                    ),
                    source_url=url,
                    apply_url=url,
                    posted_at=when(job.get("published_at")),
                )
            )
        return listings
'''


def source(args: argparse.Namespace) -> None:
    target = ROOT / "services/backend/src/apply/packs/job/sources" / f"{args.key}.py"
    if target.exists():
        sys.exit(f"{target} is already there")
    cls = "".join(part.capitalize() for part in re.split(r"[_-]", args.key))
    target.write_text(SOURCE.format(name=args.name, key=args.key, cls=cls, url=args.url, hours=args.hours))
    print(f"wrote {target.relative_to(ROOT)}\n")
    print("Then, by hand:")
    print("  1. Finish fetch() from the platform's real answer (one request, by hand), and write each label's Nepali.")
    print(f"  2. sources/__init__.py: import {cls}Source and add {cls}Source() to SOURCES.")
    print(f"  3. tests/support/recordings.py: RECORDINGS[\"{args.key}\"] = Recording(\"job\", {{config}}, {{path: answer}}, n)")
    print("     (the answer's shape as the platform gave it, with made-up postings).")
    print("  4. services/backend/src/apply/locales/es.json: the Spanish for each English label.")
    print("  5. uv run pytest tests/unit/test_every_source.py tests/unit/test_i18n.py: green when it's done.")


def board(args: argparse.Namespace) -> None:
    path = ROOT / "services/frontend/packages/ats-adapters/src/boards.json"
    data = json.loads(path.read_text())
    if args.key in data["boards"]:
        sys.exit(f"{args.key} is in boards.json already")
    for host in args.host:
        if not re.fullmatch(r"(\*\.)?[a-z0-9.-]+\.[a-z]{2,}", host):
            sys.exit(f"{host}: a host (jobs.example.com) or *.suffix (*.example.com)")
    data["boards"][args.key] = {"name": args.name, "hosts": args.host, "auto": False}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"added {args.key} to {path.relative_to(ROOT)} (extension only: \"auto\": false)\n")
    print("Then, by hand:")
    print("  1. packages/ats-adapters/src/adapters/more.ts:")
    print(f"       export const {args.key} = defineBoard({{ board: \"{args.key}\", apply: /<its form's path>/ }});")
    print(f"     and add {args.key} to MORE.")
    print("  2. tests/boards.test.ts: one of its form addresses in the \"knows %s as %s\" table.")
    print("  3. For Auto: record its form in fixtures/boards.ts, fill it in a test, then set \"auto\": true")
    print("     (and the backend's auto_boards: tests/unit/test_every_source.py says which).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    kinds = parser.add_subparsers(dest="what", required=True)
    s = kinds.add_parser("source", help="a backend source: listings from the platform's public API")
    s.add_argument("key", help="lower case, as in its address: board11")
    s.add_argument("--name", required=True, help="as people write it: board11")
    s.add_argument("--url", required=True, help="its API's base, with {company} if it's per company")
    s.add_argument("--hours", type=int, default=6, help="the least time between two asks (its terms decide)")
    b = kinds.add_parser("board", help="a board the extension fills forms on")
    b.add_argument("key")
    b.add_argument("--name", required=True)
    b.add_argument("--host", action="append", required=True, help="repeat for each: jobs.example.com, *.example.com")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", args.key):
        sys.exit("key: lower-case letters, digits and _ (as a Python name)")
    {"source": source, "board": board}[args.what](args)


if __name__ == "__main__":
    main()
