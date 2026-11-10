"""The claim check's deterministic parts: markers, numbers the profile doesn't have, quotes that must exist."""

from apply.logic.answers import recorded
from apply.logic.claims import feedback_facts, merge, rule_warnings, sentence_of, verified
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
    assert not any(q[:3] in ("201", "202") for q in numbers)  # years, and never a year's first digits
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


def test_a_year_in_a_sentence_is_read_whole_and_left_alone():
    document = "- Led payments at Himal Tech from 2021 to 2024, and grew sign-ups 3.5x in 2023.\n"
    assert [w["quote"] for w in rule_warnings(document, PROFILE)] == ["3.5x"]


def test_a_profiles_dates_back_up_no_numbers():
    profile = {"experience": [{"start": "2021-01-15", "end": "2024-06-30", "highlights": ["Ran 1,200 stores"]}]}
    document = "- Cut costs by 30% across 1,200 stores in 2023, for 15 clients.\n"
    # 30 and 15 are only the profile's month days; 1,200 is the profile's own (written the same way or not).
    assert [w["quote"] for w in rule_warnings(document, profile)] == ["30%", "15 clients"]
    assert rule_warnings("- Ran 1200 stores.\n", profile) == []


def test_a_warning_is_shown_in_its_sentence():
    document = (
        "## Professional Experience\n"
        "- Built **Django** APIs. Led a team of 12 engineers at [Himal Tech](https://example.com). Shipped weekly.\n"
    )
    assert sentence_of(document, "12 engineers") == "Led a team of 12 engineers at Himal Tech."
    assert sentence_of(document, "Django APIs") == "Built Django APIs."
    assert sentence_of(document, "Brightwater") is None
    long = "- " + "word " * 120 + "and 12 more\n"
    found = sentence_of(long, "12 more")
    assert found is not None and len(found) == 400 and found.endswith("…")


def test_corrections_and_notes_become_the_persons_own_facts():
    revision = {
        "notes": "  Say I moved to Kathmandu.  ",
        "corrections": [
            {"quote": "12 engineers", "sentence": "Led a team of 12 engineers.", "correction": "5 engineers"},
            {"quote": "fleet software", "sentence": "", "correction": ""},
        ],
    }
    facts = feedback_facts(revision)
    assert facts == {
        "corrections_from_you": [
            {"wrong": "12 engineers", "in": "Led a team of 12 engineers.", "true": "5 engineers"},
            {"wrong": "fleet software", "in": "", "true": "(take it out)"},
        ],
        "notes_from_you": "Say I moved to Kathmandu.",
    }
    assert feedback_facts(None) == {} and feedback_facts({"notes": " ", "corrections": []}) == {}
    # The corrected number is backed now.
    assert rule_warnings("- Led a team of 5 engineers.\n", {**PROFILE, **facts}) == []


def test_a_correction_stays_with_its_warning_when_checked_again():
    first = merge([], [{"kind": "number", "quote": "12 engineers", "reason": "r"}])
    wrong = [{**first[0], "resolved": "wrong", "correction": "5 engineers"}]
    again = merge(wrong, [{"kind": "number", "quote": "12 engineers", "reason": "r"}])
    assert again[0]["resolved"] == "wrong" and again[0]["correction"] == "5 engineers"
