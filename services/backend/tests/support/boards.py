"""
Job boards' public APIs, as recorded shapes: what board01, board02 and board03 answer (trimmed to the
fields apply reads, plus some it ignores). Served from the local test Site so adapters run over real HTTP.
"""

import json
from html import escape

ACME_BACKEND = {
    "id": 4012345,
    "title": "Senior Backend Engineer",
    "updated_at": "2026-10-20T10:00:00-04:00",
    "first_published": "2026-10-19T09:00:00-04:00",
    "requisition_id": "ENG-12",
    "location": {"name": "Remote - US"},
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012345",
    "content": escape(
        "<p>Build APIs in <strong>Python</strong> and Django on PostgreSQL.</p>"
        "<ul><li>5+ years Python</li><li>Celery</li></ul><p>We do not sponsor visas.</p>"
    ),
    "metadata": None,
    "departments": [{"name": "Engineering"}],
}
ACME_DESIGNER = {
    "id": 4012399,
    "title": "Product Designer",
    "updated_at": "2026-10-20T10:00:00Z",
    "location": {"name": "New York"},
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012399",
    "content": escape("<p>Figma and research.</p>"),
}

BOARD01 = {
    "/v1/boards/acme": {"name": "Acme Robotics", "content": "<p>We build robots.</p>"},
    "/v1/boards/acme/jobs": {"jobs": [ACME_BACKEND, ACME_DESIGNER], "meta": {"total": 2}},
}

BOARD02 = {
    "/v0/postings/himal": [
        {
            "id": "a1b2c3d4-0000-4000-8000-000000000001",
            "text": "Backend Engineer (Python)",
            "categories": {"location": "Kathmandu, Nepal", "team": "Platform", "commitment": "Full-time"},
            "description": "<div>Join our platform team.</div>",
            "lists": [{"text": "What you'll do", "content": "<li>Design Django APIs</li><li>Own Postgres</li>"}],
            "additional": "<div>Hybrid, 3 days in office.</div>",
            "hostedUrl": "https://jobs.lever.co/himal/a1b2c3d4-0000-4000-8000-000000000001",
            "applyUrl": "https://jobs.lever.co/himal/a1b2c3d4-0000-4000-8000-000000000001/apply",
            "createdAt": 1761300000000,
            "workplaceType": "hybrid",
            "salaryRange": {"min": 90000, "max": 120000, "currency": "USD", "interval": "per-year-salary"},
        },
    ],
}

BOARD03 = {
    "/posting-api/job-board/example-analytics": {
        "apiVersion": "1",
        "jobs": [
            {
                "id": "f3e1c2b4-1111-4111-8111-111111111111",
                "title": "Data Analyst",
                "department": "Data",
                "employmentType": "FullTime",
                "location": "Kathmandu",
                "isRemote": False,
                "workplaceType": "OnSite",
                "isListed": True,
                "descriptionHtml": "<p>SQL, dashboards and Python.</p>",
                "publishedAt": "2026-10-18T08:00:00.000+00:00",
                "jobUrl": "https://jobs.ashbyhq.com/example-analytics/f3e1c2b4-1111-4111-8111-111111111111",
                "applyUrl": "https://jobs.ashbyhq.com/example-analytics/f3e1c2b4-1111-4111-8111-111111111111/application",
                "compensation": {"compensationTierSummary": "NPR 150K – 200K"},
            },
            {
                "id": "hidden",
                "title": "Unlisted role",
                "isListed": False,
                "jobUrl": "https://jobs.ashbyhq.com/example-analytics/hidden",
            },
        ],
    },
    # A second board with the same Acme job as board01's (one match, not two) and a role no rule lets through.
    "/posting-api/job-board/acme": {
        "apiVersion": "1",
        "jobs": [
            {
                "id": "a0a0a0a0-2222-4222-8222-222222222222",
                "title": "Senior Backend Engineer",
                "employmentType": "FullTime",
                "location": "Remote (US)",
                "isRemote": True,
                "isListed": True,
                "descriptionHtml": "<p>Build APIs in Python and Django on PostgreSQL.</p>",
                "publishedAt": "2026-10-19T12:00:00.000+00:00",
                "jobUrl": "https://jobs.ashbyhq.com/acme/a0a0a0a0-2222-4222-8222-222222222222",
            },
            {
                "id": "a0a0a0a0-3333-4333-8333-333333333333",
                "title": "Go Developer",
                "employmentType": "Contract",
                "location": "Worldwide",
                "isRemote": True,
                "isListed": True,
                "descriptionHtml": "<p>Go and Kubernetes.</p>",
                "publishedAt": "2026-10-19T12:00:00.000+00:00",
                "jobUrl": "https://jobs.ashbyhq.com/acme/a0a0a0a0-3333-4333-8333-333333333333",
            },
        ],
    },
}


def serve(site, boards: dict[str, object]) -> None:
    for path, body in boards.items():
        site.add(path, json.dumps(body), content_type="application/json")


# ── other packs' sources ─────────────────────────────────────────────────────

CONTRACTS_FINDER = {
    "/Published/Notices/OCDS/Search": {
        "uri": "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search",
        "publishedDate": "2026-10-20T10:00:00Z",
        "releases": [
            {
                "ocid": "ocds-b5fd17-6b1f8a3e-1111-4c22-9a33-2b8f00000001",
                "id": "ocds-b5fd17-6b1f8a3e-1111-4c22-9a33-2b8f00000001-1",
                "date": "2026-10-19T09:00:00Z",
                "tag": ["tender"],
                "buyer": {"name": "Example City Council"},
                "parties": [
                    {
                        "name": "Example City Council",
                        "roles": ["buyer"],
                        "address": {
                            "locality": "Exampleton",
                            "region": "Yorkshire and the Humber",
                            "countryName": "England",
                        },
                        "contactPoint": {"name": "Procurement team", "email": "procurement@city.example"},
                    }
                ],
                "tender": {
                    "id": "ECC-2026-0142",
                    "title": "Case management software for children's services",
                    "description": "<p>A hosted case management system. Must meet <b>Cyber Essentials Plus</b>.</p>",
                    "status": "active",
                    "value": {"amount": 250000, "currency": "GBP"},
                    "procurementMethod": "open",
                    "procurementMethodDetails": "Open procedure",
                    "classification": {"scheme": "CPV", "id": "72000000", "description": "IT services"},
                    "tenderPeriod": {"endDate": "2026-11-30T12:00:00Z"},
                },
            },
            {
                "ocid": "ocds-b5fd17-6b1f8a3e-2222-4c22-9a33-2b8f00000002",
                "date": "2026-10-18T09:00:00Z",
                "buyer": {"name": "Example City Council"},
                "tender": {"title": "Grounds maintenance", "description": "Grass cutting.", "status": "active"},
            },
            {"ocid": "ocds-b5fd17-closed", "tender": {"title": "Old one", "status": "complete"}},
        ],
    }
}

GRANTS_GOV = {
    "/v1/api/search2": {
        "errorcode": 0,
        "msg": "Webservice Succeeds",
        "data": {
            "hitCount": 2,
            "oppHits": [
                {
                    "id": "358001",
                    "number": "EXH-27-011",
                    "title": "Rural Health Network Development Program",
                    "agencyCode": "EX-HEALTH",
                    "agency": "Example Health Agency",
                    "openDate": "10/15/2026",
                    "closeDate": "01/15/2027",
                    "oppStatus": "posted",
                    "docType": "synopsis",
                    "cfdaList": ["93.912"],
                },
                {
                    "id": "358002",
                    "number": "NSF-27-500",
                    "title": "STEM Education Research",
                    "agency": "U.S. National Science Foundation",
                    "openDate": "10/01/2026",
                    "closeDate": "",
                    "oppStatus": "forecasted",
                    "cfdaList": ["47.076"],
                },
            ],
        },
    },
    "/v1/api/fetchOpportunity": {
        "errorcode": 0,
        "data": {
            "id": 358001,
            "synopsis": {
                "synopsisDesc": "<p>Supports rural health networks that improve access to care.</p>",
                "awardCeiling": "300000",
                "awardFloor": "100000",
                "applicantEligibilityDesc": "<p>Rural nonprofit organisations.</p>",
                "agencyContactEmail": "ruralhealth@hrsa.example",
            },
        },
    },
}
