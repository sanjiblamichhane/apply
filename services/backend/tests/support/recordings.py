"""
Every source's recorded answers, for the one test every source passes (tests/unit/test_every_source.py).

Each is the shape the platform's public API answered with when the source was written (checked live, then
trimmed to what apply reads plus a few fields it ignores), with made-up postings. A source without a
recording here fails that test: adding a platform means adding its recording.

    RECORDINGS["board04"].serve(site)   # its answers, from the local test site
"""

import json
from dataclasses import dataclass, field

from .boards import BOARD01, BOARD02, BOARD03, CONTRACTS_FINDER, GRANTS_GOV


@dataclass(frozen=True)
class Recording:
    pack: str
    config: dict[str, str]
    routes: dict[str, object]  # path (with its query, when it matters) → the JSON answer, or XML as text
    listings: int  # how many postings the source should make of it
    content_type: dict[str, str] = field(default_factory=dict)  # path → its type, when not JSON

    def serve(self, site) -> None:
        for path, body in self.routes.items():
            kind = self.content_type.get(path, "application/json")
            site.add(path, body if isinstance(body, str) else json.dumps(body), content_type=kind)


DESCRIPTION = "<p>Build data pipelines in <strong>Python</strong>.</p><ul><li>3+ years</li><li>SQL</li></ul>"

BOARD05_POSTING = {
    "id": "744000158069037",
    "name": "Data Engineer",
    "uuid": "bdf82462-bcf3-4236-a766-de282f03f200",
    "refNumber": "REF2994",
    "company": {"identifier": "HimalTech", "name": "Himal Tech"},
    "releasedDate": "2026-10-27T15:02:14.350Z",
    "location": {
        "city": "Kathmandu",
        "country": "np",
        "remote": False,
        "hybrid": True,
        "fullLocation": "Kathmandu, Nepal",
    },
    "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
    "experienceLevel": {"id": "associate", "label": "Associate"},
    "visibility": "PUBLIC",
}

BOARD04_LIST = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Platform Engineer",
            "externalPath": "/job/Remote-USA/Platform-Engineer_JR2001",
            "locationsText": "Remote, USA",
            "postedOn": "Posted Today",
            "bulletFields": ["JR2001"],
        },
        {
            "title": "Data Analyst",
            "externalPath": "/job/Austin-TX/Data-Analyst_JR2002",
            "locationsText": "Austin, TX",
            "postedOn": "Posted 3 Days Ago",
            "bulletFields": ["JR2002"],
        },
    ],
    "facets": [],
    "userAuthenticated": False,
}


def board04_detail(title: str, ref: str, location: str, path: str) -> dict[str, object]:
    return {
        "jobPostingInfo": {
            "id": f"7fbda13c{ref}",
            "title": title,
            "jobDescription": DESCRIPTION,
            "location": location,
            "postedOn": "Posted Today",
            "startDate": "2026-10-20",
            "timeType": "Full time",
            "jobReqId": ref,
            "externalUrl": f"https://acme.wd5.myworkdayjobs.com/External{path}",
            "canApply": True,
        },
        "hiringOrganization": {"name": "US01 Acme Holdings LLC", "url": ""},
        "userAuthenticated": False,
    }


BOARD08_XML = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
<position>
    <id>1834171</id>
    <subcompany>Himal Tech GmbH</subcompany>
    <office>Munich</office>
    <additionalOffices><office>Berlin</office></additionalOffices>
    <department>Engineering</department>
    <name>Backend Engineer (Python)</name>
    <jobDescriptions>
        <jobDescription>
            <name>Your role</name>
            <value><![CDATA[<p>Build APIs in <strong>Python</strong>.</p>]]></value>
        </jobDescription>
        <jobDescription>
            <name>About you</name>
            <value><![CDATA[<ul><li>Django</li><li>PostgreSQL</li></ul>]]></value>
        </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <createdAt>2026-10-20T09:00:00+00:00</createdAt>
</position>
</workzag-jobs>
"""

RECORDINGS: dict[str, Recording] = {
    # ── the job pack: company boards ────────────────────────────────────────
    "board01": Recording("job", {"board": "acme"}, BOARD01, 2),
    "board02": Recording("job", {"company": "himal", "display": "Himal Tech"}, BOARD02, 1),
    "board03": Recording("job", {"board": "example-analytics", "company": "Example Analytics"}, BOARD03, 1),
    "board04": Recording(
        "job",
        {"careers_url": "https://acme.wd5.myworkdayjobs.com/en-US/External", "company": "Acme"},
        {
            "/wday/cxs/acme/External/jobs": BOARD04_LIST,
            "/wday/cxs/acme/External/job/Remote-USA/Platform-Engineer_JR2001": board04_detail(
                "Platform Engineer", "JR2001", "Remote, USA", "/job/Remote-USA/Platform-Engineer_JR2001"
            ),
            "/wday/cxs/acme/External/job/Austin-TX/Data-Analyst_JR2002": board04_detail(
                "Data Analyst", "JR2002", "Austin, TX", "/job/Austin-TX/Data-Analyst_JR2002"
            ),
        },
        2,
    ),
    "board05": Recording(
        "job",
        {"company": "HimalTech"},
        {
            "/v1/companies/HimalTech/postings": {
                "offset": 0,
                "limit": 100,
                "totalFound": 1,
                "content": [BOARD05_POSTING],
            },
            "/v1/companies/HimalTech/postings/744000158069037": BOARD05_POSTING
            | {
                "postingUrl": "https://jobs.smartrecruiters.com/HimalTech/744000158069037-data-engineer",
                "applyUrl": "https://jobs.smartrecruiters.com/HimalTech/744000158069037-data-engineer?oga=true",
                "jobAd": {
                    "sections": {
                        "companyDescription": {"title": "Company Description", "text": "<p>We build software.</p>"},
                        "jobDescription": {"title": "Job Description", "text": DESCRIPTION},
                        "qualifications": {"title": "Qualifications", "text": "<ul><li>Airflow</li></ul>"},
                        "additionalInformation": {"title": "Additional Information", "text": "<p>Visa support.</p>"},
                    }
                },
            },
        },
        1,
    ),
    "board06": Recording(
        "job",
        {"account": "himaltech"},
        {
            "/api/v1/widget/accounts/himaltech": {
                "name": "Himal Tech",
                "description": "<p>We build software.</p>",
                "jobs": [
                    {
                        "title": "Machine Learning Engineer",
                        "shortcode": "81B46579FE",
                        "employment_type": "Full-time",
                        "telecommuting": True,
                        "department": "Engineering",
                        "url": "https://apply.workable.com/j/81B46579FE",
                        "shortlink": "https://apply.workable.com/j/81B46579FE",
                        "application_url": "https://apply.workable.com/j/81B46579FE/apply",
                        "published_on": "2026-10-20",
                        "created_at": "2026-10-20",
                        "country": "Nepal",
                        "city": "Kathmandu",
                        "locations": [{"country": "Nepal", "countryCode": "NP", "city": "Kathmandu", "hidden": False}],
                        "description": DESCRIPTION,
                    }
                ],
            }
        },
        1,
    ),
    "board07": Recording(
        "job",
        {"company": "himaltech"},
        {
            "/api/offers/": {
                "offers": [
                    {
                        "id": 2207001,
                        "slug": "backend-engineer",
                        "title": "Backend Engineer",
                        "status": "published",
                        "company_name": "Himal Tech",
                        "description": DESCRIPTION,
                        "requirements": "<p>Django and PostgreSQL.</p>",
                        "location": "Amsterdam, Netherlands",
                        "remote": False,
                        "hybrid": True,
                        "on_site": False,
                        "employment_type_code": "fulltime_permanent",
                        "salary": {"min": "60000", "max": "80000", "currency": "EUR", "period": "year"},
                        "careers_url": "https://himaltech.recruitee.com/o/backend-engineer",
                        "careers_apply_url": "https://himaltech.recruitee.com/o/backend-engineer/c/new",
                        "published_at": "2026-10-26 13:02:53 UTC",
                    },
                    {
                        "id": 2207002,
                        "title": "Draft role",
                        "status": "draft",
                        "careers_url": "https://x.recruitee.com/o/d",
                    },
                ]
            }
        },
        1,
    ),
    "board08": Recording(
        "job",
        {"company": "himaltech"},
        {"/xml": BOARD08_XML},
        1,
        content_type={"/xml": "text/xml"},
    ),
    "board09": Recording(
        "job",
        {"company": "himaltech"},
        {
            "/json": [
                {
                    "id": "98323abf2296",
                    "friendly_id": "98323abf2296-support-engineer",
                    "name": "Support Engineer",
                    "url": "https://himaltech.breezy.hr/p/98323abf2296-support-engineer",
                    "published_date": "2026-10-15T14:37:22.684Z",
                    "type": {"id": "fullTime", "name": "Full-Time"},
                    "location": {"name": "Pokhara, NP", "city": "Pokhara", "is_remote": False},
                    "department": "Support",
                    "salary": "NPR 80,000 – 100,000 / month",
                    "company": {"name": "Himal Tech", "friendly_id": "himaltech"},
                }
            ]
        },
        1,
    ),
    # ── the job pack: job sites ─────────────────────────────────────────────
    # ── other packs ──────────────────────────────────────────────────────────
    "contracts_finder": Recording("tender", {}, CONTRACTS_FINDER, 2),
    "grants_gov": Recording("grant", {"keyword": "rural health"}, GRANTS_GOV, 2),
}
