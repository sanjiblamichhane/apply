"""The claim check's deterministic parts: markers, numbers the profile doesn't have, quotes that must exist."""

from apply.logic.answers import recorded
from apply.logic.claims import merge, rule_warnings, verified
from apply.store.sql.models import Answer

PROFILE = {
    "full_name": "Sam Rai",
    "email": "sam@example.com",
    "experience": [
        {
            "title": "Backend Engineer",
            "organisation": "Himal Tech",
            "start": "2019",
            "end": "2025",
            "highlights": ["Built Django REST APIs on PostgreSQL", "Cut page load by 40%"],
        }
    ],
}

DOCUMENT = """# Sam Rai
sam@example.com | +977 1 4412345 | https://linkedin.com/in/example

- Backend Engineer, Himal Tech, 2019 – 2025
- Cut page load by 40%
- Led a team of 12 engineers and saved $2M a year
- Mentored [CONFIRM: how many] juniors
"""


def test_markers_and_unbacked_numbers_are_flagged_but_the_profiles_own_are_not():
    found = rule_warnings(DOCUMENT, PROFILE)
    kinds = [(w["kind"], w["quote"]) for w in found]
    assert ("confirm", "[CONFIRM: how many]") in kinds
    numbers = [q for k, q in kinds if k == "number"]
    assert any("12" in q for q in numbers) and any("2M" in q for q in numbers)
    assert not any("40" in q for q in numbers)  # in the profile
    assert not any(q in ("2019", "2025") for q in numbers)  # years
    assert not any("4412345" in q for q in numbers)  # contact line


def test_a_letters_date_is_no_claim():
    letter = "# Sam Rai\n\nOctober 27, 2026\n\n27 October 2026\n\nDear Hiring Manager,\n\nI led 12 engineers."
    assert [w["quote"] for w in rule_warnings(letter, PROFILE)] == ["12 engineers"]


def test_only_quotes_really_in_the_document_count():
    claims = [
        {"quote": "Led a team of 12 engineers", "reason": "Not in the profile"},
        {"quote": "Built fleet software at Acme", "reason": "Invented"},  # not in the document
        {"quote": "x", "reason": "Too short to mean anything"},
    ]
    found = verified(DOCUMENT, claims)
    assert [w["quote"] for w in found] == ["Led a team of 12 engineers"]


def test_decisions_carry_over_to_the_same_words():
    first = merge([], [{"kind": "unsupported", "quote": "Led a team of 12", "reason": "r"}])
    first[0]["resolved"] = "kept"
    again = merge(
        first,
        [
            {"kind": "unsupported", "quote": "led a  team of 12", "reason": "r2"},
            {"kind": "unsupported", "quote": "Led a team of 12", "reason": "dup"},
        ],
    )
    assert len(again) == 1 and again[0]["resolved"] == "kept"


def test_a_sensitive_answer_is_recorded_only_as_provided_or_declined():
    gender = Answer(key="gender", question={"en": "Gender"}, answer="woman", is_sensitive=True)
    assert recorded(gender) == {"key": "gender", "question": "Gender", "state": "provided"}
    gender.answer = "decline"
    assert recorded(gender)["state"] == "declined" and "value" not in recorded(gender)
    notice = Answer(key="notice_period", question={"en": "Notice"}, answer="1 month", is_sensitive=False)
    assert recorded(notice)["value"] == "1 month"
