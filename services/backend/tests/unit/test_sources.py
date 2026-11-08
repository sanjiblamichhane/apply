"""Each board's adapter over real HTTP (recorded API shapes from the local Site): what it reads into the job pack."""

from datetime import UTC, datetime

import pytest

from apply.errors import ApplyError
from apply.libs.extract import FetchConfig, Fetcher, FetchError
from apply.packs import get_pack
from tests.support.boards import BOARD01, BOARD02, BOARD03, serve


@pytest.fixture
async def fetcher():
    f = Fetcher(FetchConfig(version="test", allow_private=True))
    yield f
    await f.aclose()


def adapter(kind: str):
    return get_pack("job").source(kind)


async def test_greenhouse(site, fetcher):
    serve(site, BOARD01)
    listings = await adapter("board01").fetch(fetcher, {"board": "acme"}, site.url)
    backend, designer = listings
    assert backend.ref == "4012345" and backend.title == "Senior Backend Engineer"
    assert backend.issuer_name == "Acme Robotics"  # from the board, when not given
    assert backend.attributes["workplace"] == "remote" and backend.attributes["location"] == "Remote - US"
    assert "**Python**" in backend.attributes["description_markdown"]  # its HTML is escaped once more; undone
    assert backend.source_url == "https://boards.greenhouse.io/acme/jobs/4012345"
    assert backend.posted_at == datetime(2026, 10, 19, 13, 0, tzinfo=UTC)
    assert designer.attributes["workplace"] == ""
    assert any("content=true" in path for path, _ in site.hits)


async def test_lever(site, fetcher):
    serve(site, BOARD02)
    [job] = await adapter("board02").fetch(fetcher, {"company": "himal", "display": "Himal Tech"}, site.url)
    assert job.issuer_name == "Himal Tech" and job.title == "Backend Engineer (Python)"
    assert job.attributes["workplace"] == "hybrid" and job.attributes["employment_type"] == "Full-time"
    assert job.attributes["salary_text"] == "USD 90,000 – 120,000 a year"
    assert "## What you'll do" in job.attributes["description_markdown"]
    assert job.apply_url.endswith("/apply")
    assert job.posted_at is not None and job.posted_at.year == 2025


async def test_ashby_skips_unlisted_roles(site, fetcher):
    serve(site, BOARD03)
    [job] = await adapter("board03").fetch(
        fetcher, {"board": "example-analytics", "company": "Example Analytics"}, site.url
    )
    assert job.title == "Data Analyst" and job.attributes["workplace"] == "onsite"
    assert job.attributes["employment_type"] == "Full time" and job.attributes["salary_text"] == "NPR 150K – 200K"


def test_config_is_checked():
    with pytest.raises(ApplyError):
        adapter("board01").validate_config({})
    with pytest.raises(ApplyError):
        adapter("board01").validate_config({"board": "../../etc/passwd"})
    assert adapter("board01").validate_config({"board": " acme ", "company": ""}) == {"board": "acme"}


def test_every_adapter_says_what_it_needs_in_both_languages():
    for source in get_pack("job").sources:
        described = source.describe()
        assert described["terms"]["en"] and described["terms"]["ne"]
        assert all(f["label"]["ne"] and f["hint"]["ne"] for f in described["fields"])


# ── the platforms added after the first four ─────────────────────────────────


def recorded(kind: str, site):
    from tests.support.recordings import RECORDINGS

    recording = RECORDINGS[kind]
    recording.serve(site)
    return adapter(kind), recording.config


async def test_workday_reads_the_careers_site_and_links_its_apply_page(site, fetcher):
    board04, config = recorded("board04", site)
    platform, analyst = await board04.fetch(fetcher, board04.validate_config(config), site.url)
    assert platform.ref == "JR2001" and platform.issuer_name == "Acme"
    assert platform.attributes["workplace"] == "remote" and platform.attributes["employment_type"] == "Full time"
    assert "**Python**" in platform.attributes["description_markdown"]
    assert platform.source_url == "https://acme.wd5.myworkdayjobs.com/External/job/Remote-USA/Platform-Engineer_JR2001"
    assert platform.apply_url == platform.source_url + "/apply"
    assert analyst.attributes["workplace"] == ""
    asked = [path for path, _ in site.hits]
    assert asked[0] == "/wday/cxs/acme/External/jobs"  # one page: fewer than 20 came back


def test_workday_takes_only_a_workday_careers_address():
    from apply.errors import ApplyError
    from apply.packs.job.sources.board04 import parse_site

    board04 = adapter("board04")
    assert parse_site("https://acme.wd5.myworkdayjobs.com/en-US/AcmeExternalCareerSite") == (
        "acme.wd5.myworkdayjobs.com",
        "acme",
        "AcmeExternalCareerSite",
    )
    for wrong in (
        "https://evil.example/External",
        "http://acme.wd5.myworkdayjobs.com/External",
        "https://acme.wd5.myworkdayjobs.com.evil.example/External",
    ):
        with pytest.raises(ApplyError):
            board04.validate_config({"careers_url": wrong})


async def test_workday_stops_at_its_cap(site, fetcher):
    from apply.packs.job.sources import board04 as module

    page = {
        "total": 500,
        "jobPostings": [{"title": f"Role {n}", "externalPath": f"/job/X/Role_{n}"} for n in range(module.PAGE)],
    }
    site.add("/wday/cxs/acme/External/jobs", __import__("json").dumps(page), content_type="application/json")
    listings = await adapter("board04").fetch(
        fetcher, {"careers_url": "https://acme.wd5.myworkdayjobs.com/External"}, site.url
    )
    assert len(listings) == module.MAX_POSTINGS
    assert sum(1 for path, _ in site.hits if path.endswith("/jobs")) == module.MAX_POSTINGS // module.PAGE


async def test_smartrecruiters_lists_a_posting_even_when_its_details_fail(site, fetcher):
    from tests.support.recordings import BOARD05_POSTING

    site.add(
        "/v1/companies/HimalTech/postings",
        __import__("json").dumps({"content": [BOARD05_POSTING]}),
        content_type="application/json",
    )
    [job] = await adapter("board05").fetch(fetcher, {"company": "HimalTech"}, site.url)
    assert job.title == "Data Engineer" and job.attributes["description_markdown"] == ""
    assert job.source_url == "https://jobs.smartrecruiters.com/HimalTech/744000158069037"
    assert job.attributes["workplace"] == "hybrid"


async def test_smartrecruiters_keeps_the_sections_that_say_what_the_job_is(site, fetcher):
    smart, config = recorded("board05", site)
    [job] = await smart.fetch(fetcher, config, site.url)
    description = job.attributes["description_markdown"]
    assert "### Job Description" in description and "### Qualifications" in description
    assert "We build software" not in description  # the company's blurb isn't the job


async def test_personio_reads_its_feed_and_refuses_one_with_entities(site, fetcher):
    board08, config = recorded("board08", site)
    [job] = await board08.fetch(fetcher, config, site.url)
    assert job.issuer_name == "Himal Tech GmbH" and job.attributes["location"] == "Munich · Berlin"
    assert job.attributes["employment_type"] == "full time permanent"
    assert job.source_url == "https://himaltech.jobs.personio.de/job/1834171"
    assert "### About you" in job.attributes["description_markdown"]

    site.add("/xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "a">]><workzag-jobs/>', content_type="text/xml")
    with pytest.raises(FetchError, match="DTD"):
        await board08.fetch(fetcher, config, site.url)


async def test_recruitee_skips_drafts_and_reads_its_pay(site, fetcher):
    board07, config = recorded("board07", site)
    [job] = await board07.fetch(fetcher, config, site.url)
    assert job.attributes["salary_text"] == "EUR 60,000 – 80,000 a year"
    assert job.attributes["workplace"] == "hybrid" and job.posted_at is not None
