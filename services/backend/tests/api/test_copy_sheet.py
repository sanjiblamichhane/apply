"""The extension's copy panel: a profile's values ready to paste, saved answers, and the token scope it needs."""

from .helpers import PROFILE
from .test_extension import ALL, extension, make_token

FULL = {
    **PROFILE,
    "attributes": {
        **PROFILE["attributes"],
        "full_name": "Sam Bahadur Rai",
        "phone": "9800000000",
        "phone_country_code": "+977",
        "address_line1": "Ward 4, Lazimpat",
        "city": "Kathmandu",
        "region": "Bagmati",
        "postal_code": "44600",
        "country": "Nepal",
        "links": [{"label": "Network profile", "url": "https://www.linkedin.com/in/example"}],
        "work_authorization": "Citizen of Nepal",
        "experience": [
            {
                "title": "Backend Engineer",
                "organisation": "Himal Tech",
                "start": "Jan 2021",
                "end": "",
                "highlights": ["Built Django REST APIs on PostgreSQL", "Moved slow work to Celery"],
            }
        ],
    },
}


def values(sheet: dict, tab: str) -> dict[str, str]:
    """A tab's values by their English label (first group, or all groups merged)."""
    found = next(t for t in sheet["tabs"] if t["key"] == tab)
    return {i["label"]["en"]: i["value"] for g in found["groups"] for i in g["items"]}


async def test_the_profile_comes_ready_to_paste(client, owner):
    made = (await client.post("/api/v1/profiles", json=FULL)).json()
    sheet = (await client.get("/api/v1/copy-sheet")).json()
    assert sheet["profile"]["id"] == made["id"] and sheet["profile"]["is_default"]
    assert [t["key"] for t in sheet["tabs"]] == ["basics", "experience", "education", "more"]
    basics = values(sheet, "basics")
    assert basics["First name"] == "Sam" and basics["Middle name"] == "Bahadur" and basics["Last name"] == "Rai"
    assert basics["Phone, international"] == "+977 9800000000"
    assert basics["Address line 1"] == "Ward 4, Lazimpat" and basics["Postcode or ZIP"] == "44600"
    assert basics["Network profile"] == "https://www.linkedin.com/in/example"
    job = next(t for t in sheet["tabs"] if t["key"] == "experience")["groups"][0]
    assert job["title"] == "Backend Engineer, Himal Tech"
    jobs = {i["label"]["en"]: i["value"] for i in job["items"]}
    assert jobs["From"] == "Jan 2021" and jobs["From (MM/YYYY)"] == "01/2021" and jobs["From (YYYY-MM)"] == "2021-01"
    assert jobs["What you did"] == "• Built Django REST APIs on PostgreSQL\n• Moved slow work to Celery"
    assert "All of it" not in jobs  # each field once: no tile repeating the whole job
    more = values(sheet, "more")
    assert more["Skills, with commas"] == "Python, Django, PostgreSQL, Celery, React"
    assert more["Right to work"] == "Citizen of Nepal"
    # Labels come in every language the panel speaks.
    assert next(t for t in sheet["tabs"] if t["key"] == "basics")["label"]["ne"]


async def test_saved_answers_are_there_and_sensitive_ones_are_marked(client, owner):
    await client.post("/api/v1/profiles", json=FULL)
    await client.post("/api/v1/answers/defaults", json={"pack": "job"})
    answers = {a["key"]: a for a in (await client.get("/api/v1/answers", params={"pack": "job"})).json()["items"]}
    await client.patch(f"/api/v1/answers/{answers['notice_period']['id']}", json={"answer": "One month"})
    await client.patch(f"/api/v1/answers/{answers['gender']['id']}", json={"answer": "woman"})
    await client.patch(f"/api/v1/answers/{answers['needs_sponsorship']['id']}", json={"answer": "no"})
    sheet = (await client.get("/api/v1/copy-sheet")).json()
    items = {i["label"]["en"]: i for g in sheet["tabs"][-1]["groups"] for i in g["items"]}
    notice = next(i for q, i in items.items() if "notice" in q.lower())
    assert notice["value"] == "One month" and not notice["sensitive"]
    gender = next(i for q, i in items.items() if "gender" in q.lower())
    assert gender["sensitive"]
    sponsorship = next(i for q, i in items.items() if "sponsorship" in q.lower())
    assert sponsorship["value"] == "No"


async def test_another_profile_can_be_chosen_and_none_is_said_plainly(client, owner, other_client):
    first = (await client.post("/api/v1/profiles", json=FULL)).json()
    second = (await client.post("/api/v1/profiles", json={**FULL, "name": "Data"})).json()
    chosen = (await client.get("/api/v1/copy-sheet", params={"profile_id": second["id"]})).json()
    assert chosen["profile"]["id"] == second["id"] and {p["id"] for p in chosen["profiles"]} == {
        first["id"],
        second["id"],
    }
    nothing = (await other_client.get("/api/v1/copy-sheet")).json()
    assert nothing == {"profile": None, "profiles": [], "tabs": []}
    # Someone else's profile isn't theirs to read.
    assert (await other_client.get("/api/v1/copy-sheet", params={"profile_id": first["id"]})).status_code == 404


async def test_a_token_needs_profiles_read(client, owner):
    await client.post("/api/v1/profiles", json=FULL)
    without = await make_token(client, ALL)
    async with extension(client, without["secret"]) as ext:
        denied = await ext.get("/api/v1/copy-sheet")
        assert denied.status_code == 403 and denied.json()["code"] == "TOKEN_SCOPE_MISSING"
    with_scope = await make_token(client, [*ALL, "profiles:read"])
    async with extension(client, with_scope["secret"]) as ext:
        sheet = await ext.get("/api/v1/copy-sheet")
        assert sheet.status_code == 200 and sheet.json()["profile"]["name"] == "Backend"
        # Reading profiles is all it adds: it still can't change one.
        assert (await ext.post("/api/v1/profiles", json=FULL)).status_code in (401, 403)
