"""Small helpers the API tests share."""

POSTING = """Senior Backend Engineer at Acme Robotics (remote).
We build fleet software in Python and Django on PostgreSQL, with Celery and Redis for background work.
You will design APIs, own reliability, and mentor two engineers.
Requirements: 5+ years Python, Django REST Framework, PostgreSQL, Celery."""

PROFILE = {
    "pack": "job",
    "kind": "individual",
    "name": "Backend",
    "summary": "Backend engineer who ships reliable APIs.",
    "attributes": {
        "full_name": "Sam Rai",
        "email": "sam@example.com",
        "skills": ["Python", "Django", "PostgreSQL", "Celery", "React"],
        "experience": [
            {
                "title": "Backend Engineer",
                "organisation": "Himal Tech",
                "start": "2019",
                "end": "2025",
                "highlights": ["Built Django REST APIs on PostgreSQL", "Moved slow work to Celery"],
            }
        ],
        "education": [
            {"qualification": "BE Computer Engineering", "institution": "Example University", "year": "2018"}
        ],
    },
}

EXTRACTED = {
    "job_title": "Senior Backend Engineer",
    "company_name": "Acme Robotics",
    "description_markdown": "- Python, Django, PostgreSQL\n- Design APIs",
    "location": "",
    "workplace": "remote",
    "employment_type": "",
    "salary_text": "",
    "visa_sponsorship_text": "",
    "hiring_manager": "",
}


def ld_page(posting: dict) -> str:
    import json

    return (
        f'<html><head><title>Careers</title><script type="application/ld+json">{json.dumps(posting)}</script>'
        "</head><body><h1>Careers</h1><p>Apply below.</p></body></html>"
    )
