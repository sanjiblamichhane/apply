"""Search rules, the dedupe key, score parsing and briefing timing: the deterministic parts of discovery."""

from datetime import UTC, datetime

import pytest

from apply.libs.llm import LLMError
from apply.logic.briefings import due, local_date
from apply.logic.matches import parse_score
from apply.logic.searches import Criteria, evaluate, says_no_sponsorship
from apply.packs import get_pack
from apply.packs.base import Searchable
from apply.store.sql.models import User

POSTING = Searchable(
    title="Senior Backend Engineer",
    body="Python, Django and PostgreSQL. Some Go.",
    location="Kathmandu, Nepal",
    remote=False,
    sponsorship="",
)


@pytest.mark.parametrize(
    ("criteria", "passes"),
    [
        ({}, True),
        ({"keywords": ["django", "rust"]}, True),
        ({"keywords": ["django", "rust"], "match_all": True}, False),
        ({"keywords": ["go"]}, True),
        ({"keywords": ["goo"]}, False),  # whole words only
        ({"exclude": ["senior"]}, False),  # excluded words look at the title
        ({"exclude": ["python"]}, True),
        ({"locations": ["Kathmandu"]}, True),
        ({"locations": ["Pokhara"]}, False),
        ({"remote_only": True}, False),
    ],
)
def test_rules(criteria, passes):
    assert evaluate(Criteria.model_validate(criteria), POSTING)[0] is passes


def test_a_remote_posting_passes_a_location_rule_and_says_why():
    remote = Searchable(title="Backend", body="python", location="Anywhere", remote=True, sponsorship="")
    passed, why = evaluate(Criteria(keywords=["Python"], locations=["Kathmandu"]), remote)
    assert passed and why == {"keywords": ["Python"], "locations": [], "remote": True}


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("We do not sponsor visas.", True),
        ("Unable to provide visa sponsorship at this time", True),
        ("Must be authorized to work without sponsorship", True),
        ("US citizens only", True),
        ("We sponsor visas for strong candidates", False),
        ("", False),
    ],
)
def test_no_sponsorship(text, says):
    assert says_no_sponsorship(text) is says


def test_the_same_job_on_two_boards_has_one_key():
    pack = get_pack("job")
    a = pack.dedupe_key("Acme Robotics, Inc.", "Sr. Backend Engineer", {"location": "Remote – US"})
    b = pack.dedupe_key("ACME ROBOTICS", "Senior Backend Engineer", {"location": "remote us"})
    assert a == b
    assert a != pack.dedupe_key("Acme Robotics", "Senior Frontend Engineer", {"location": "remote us"})
    # Boards word one remote job differently; the same title in two cities is two jobs.
    assert a == pack.dedupe_key(
        "Acme Robotics", "Senior Backend Engineer", {"location": "Remote (USA)", "workplace": "remote"}
    )
    assert pack.dedupe_key("Acme", "Engineer", {"location": "Kathmandu"}) != pack.dedupe_key(
        "Acme", "Engineer", {"location": "Pokhara"}
    )


def test_a_score_is_held_to_its_bounds():
    assert parse_score({"fit_score": 140, "reasons": ["a", " ", "b", "c", "d"], "dealbreakers": ["Needs TS/SCI"]}) == (
        100,
        ["a", "b", "c"],
        [{"text": "Needs TS/SCI"}],
    )
    assert parse_score({"fit_score": "-5", "reasons": [], "dealbreakers": []})[0] == 0
    with pytest.raises(LLMError):
        parse_score({"fit_score": "excellent", "reasons": [], "dealbreakers": []})


def test_the_briefing_is_due_at_the_owners_hour_in_their_time_zone():
    user = User(email="a@b.c", password_hash="x", time_zone="Asia/Kathmandu", briefing_hour=7)
    early = datetime(2026, 10, 26, 0, 30, tzinfo=UTC)  # 06:15 in Kathmandu
    later = datetime(2026, 10, 26, 1, 30, tzinfo=UTC)  # 07:15
    assert not due(user, early, has_today=False)
    assert due(user, later, has_today=False)
    assert not due(user, later, has_today=True)
    assert local_date(user, datetime(2026, 10, 25, 20, 0, tzinfo=UTC)) == "2026-10-26"  # already tomorrow there
    user.time_zone = "Not/AZone"
    assert local_date(user, later) == "2026-10-26"  # falls back to UTC
