"""The claim check on the real model: an invented employer and an invented result are caught; facts aren't."""

import time

from apply.logic.claims import rule_warnings, verified
from apply.packs import get_pack
from apply.packs.base import ProfileInput
from tests.api.helpers import PROFILE

DOCUMENT = """# Sam Rai
sam@example.com

### Experience
- Backend Engineer, Himal Tech (2019 – 2025): built Django REST APIs on PostgreSQL and moved slow work to Celery.
- Senior Engineer, Brightwater Logistics (2015 – 2019): led the Kubernetes migration for 300 services.
"""


async def test_the_model_flags_what_the_profile_doesnt_back(live_model):
    pack = get_pack("job")
    profile = ProfileInput(name="Backend", summary=PROFILE["summary"], attributes=PROFILE["attributes"])
    prompt = pack.claims_prompt(DOCUMENT, profile)
    started = time.monotonic()
    data = await live_model.complete_json(prompt.text, pack.claims_schema, purpose=prompt.purpose)
    found = verified(DOCUMENT, data.get("claims") or [])
    print(f"\n[live] claim check took {time.monotonic() - started:.1f}s: {[w['quote'] for w in found]}")
    quotes = " | ".join(w["quote"] for w in found).lower()
    assert "brightwater" in quotes or "kubernetes" in quotes, found
    assert "himal tech" not in quotes, "A fact from the profile was flagged"
    numbers = [w["quote"] for w in rule_warnings(DOCUMENT, {"name": "Backend", **PROFILE["attributes"]})]
    assert any("300" in q for q in numbers)
    await live_model.aclose()
