"""Reading JobPosting JSON-LD wherever a page puts it, and the job pack's mapping of it."""

import json
from datetime import UTC, datetime

from apply.libs.extract import find_nodes, page_text, to_markdown
from apply.packs import get_pack

POSTING = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Senior Backend Engineer",
    "description": "<p>Build <strong>APIs</strong>.</p><ul><li>Python</li><li>Postgres</li></ul>",
    "hiringOrganization": {"@type": "Organization", "name": "Acme Robotics"},
    "jobLocation": {
        "@type": "Place",
        "address": {"addressLocality": "Austin", "addressRegion": "TX", "addressCountry": "US"},
    },
    "employmentType": ["FULL_TIME"],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "currency": "USD",
        "value": {"@type": "QuantitativeValue", "minValue": 120000, "maxValue": 150000, "unitText": "YEAR"},
    },
    "validThrough": "2026-12-01",
}


def page(*blocks: object) -> str:
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blocks)
    return f"<html><head>{scripts}</head><body><h1>Jobs</h1></body></html>"


def test_found_as_an_object_in_a_list_and_in_a_graph():
    for html in (
        page(POSTING),
        page([{"@type": "WebSite"}, POSTING]),
        page({"@context": "https://schema.org", "@graph": [{"@type": "Organization"}, POSTING]}),
    ):
        nodes = find_nodes(html, {"JobPosting"})
        assert [n["title"] for n in nodes] == ["Senior Backend Engineer"]


def test_type_written_as_a_url_or_a_list_counts():
    assert find_nodes(page(POSTING | {"@type": "https://schema.org/JobPosting"}), {"JobPosting"})
    assert find_nodes(page(POSTING | {"@type": ["Thing", "JobPosting"]}), {"JobPosting"})


def test_broken_json_and_other_types_are_skipped():
    html = '<script type="application/ld+json">{oops</script>' + page({"@type": "Organization"})
    assert find_nodes(html, {"JobPosting"}) == []


def test_the_job_pack_maps_a_posting():
    extracted = get_pack("job").from_json_ld(POSTING, "https://jobs.example.com/1")
    assert extracted is not None
    assert extracted.title == "Senior Backend Engineer"
    assert extracted.issuer_name == "Acme Robotics"
    attrs = extracted.attributes
    assert attrs["location"] == "Austin, TX, US"
    assert attrs["salary_text"] == "USD 120,000 – 150,000 a year"
    assert attrs["employment_type"] == "Full time"
    assert "- Python" in attrs["description_markdown"] and "**APIs**" in attrs["description_markdown"]
    assert extracted.deadline == datetime(2026, 12, 1, 23, 59, tzinfo=UTC)
    assert extracted.apply_url == "https://jobs.example.com/1"


def test_remote_postings_and_missing_fields():
    remote = {
        "@type": "JobPosting",
        "title": "Data Analyst",
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": {"@type": "Country", "name": "Nepal"},
    }
    extracted = get_pack("job").from_json_ld(remote, "https://x.example/2")
    assert extracted.attributes["workplace"] == "remote"
    assert extracted.attributes["location"] == "Remote (Nepal)"
    assert extracted.attributes["salary_text"] == ""
    assert extracted.issuer_name == ""
    assert extracted.deadline is None


def test_a_posting_without_a_title_is_not_used():
    assert get_pack("job").from_json_ld({"@type": "JobPosting", "description": "x"}, "https://x.example") is None


def test_html_to_markdown_and_page_text():
    assert to_markdown("<h2>Role</h2><p>Do&nbsp;things</p><ul><li>One</li></ul>") == "## Role\n\nDo things\n\n- One"
    html = "<html><nav>Menu</nav><main><h1>Title</h1><p>Body text</p><script>x()</script></main><footer>F</footer>"
    text = page_text(html)
    assert "Menu" not in text and "x()" not in text and "F" not in text
    assert "Title" in text and "Body text" in text
