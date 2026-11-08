"""The job pack: its fields, its pipeline, its prompts."""

from datetime import date

import pytest

from apply.errors import ApplyError, ErrorCode
from apply.packs import all_packs, get_pack
from apply.packs.base import OpportunityInput, ProfileInput, fill

PROFILE = {
    "full_name": "Sam Rai",
    "email": "sam@example.com",
    "skills": ["Python", "Django"],
    "experience": [
        {
            "title": "Backend Engineer",
            "organisation": "Himal Tech",
            "start": "2019",
            "end": "2025",
            "highlights": ["Built Django REST APIs on PostgreSQL"],
        }
    ],
    "education": [{"qualification": "BE Computer Engineering", "institution": "Example University", "year": "2018"}],
}


def test_the_profile_fields_accept_a_profile_and_refuse_unknown_keys():
    pack = get_pack("job")
    assert pack.validate_profile(PROFILE)["experience"][0]["organisation"] == "Himal Tech"
    with pytest.raises(ApplyError) as caught:
        pack.validate_profile(PROFILE | {"favourite_colour": "teal"})
    assert caught.value.code == ErrorCode.INVALID_ATTRIBUTES
    assert caught.value.extra["errors"][0]["loc"] == ["favourite_colour"]


def test_links_must_be_web_links():
    with pytest.raises(ApplyError):
        get_pack("job").validate_profile({"links": [{"label": "x", "url": "javascript:alert(1)"}]})


def test_the_pipeline_starts_in_one_place_and_ends_in_terminal_stages():
    stages = get_pack("job").pipeline.stages
    codes = [s.code for s in stages]
    assert codes[0] == "new" and len(set(codes)) == len(codes)
    assert {s.code for s in stages if s.is_terminal} == {"declined", "cancelled", "accepted"}
    assert all(s.category in ("success", "failure") for s in stages if s.is_terminal)


def test_document_types():
    pack = get_pack("job")
    assert pack.document_type("resume").generatable and pack.document_type("cover_letter").generatable
    assert not pack.document_type("job_description").generatable
    with pytest.raises(ApplyError) as caught:
        pack.document_type("haiku")
    assert caught.value.code == ErrorCode.DOCUMENT_TYPE_NOT_FOUND


@pytest.mark.parametrize("kind", ["resume", "cover_letter"])
def test_the_prompts_carry_the_profile_the_posting_and_the_rule_against_inventing(kind):
    prompt = get_pack("job").document_prompt(
        kind,
        ProfileInput(
            name="Sam Rai", summary="Backend engineer", attributes=PROFILE, tone_instructions="Warm, plain English"
        ),
        OpportunityInput(
            title="Senior Backend Engineer",
            issuer_name="Acme",
            attributes={
                "job_title": "Senior Backend Engineer",
                "company_name": "Acme Robotics",
                "description_markdown": "Python and Django on PostgreSQL.",
            },
        ),
        date(2026, 10, 26),
    )
    assert prompt.purpose == "writing"
    text = prompt.text
    assert "Himal Tech" in text and "Example University" in text
    assert "Python and Django on PostgreSQL." in text
    assert "use only facts from PROFILE" in text and "[CONFIRM:" in text
    assert "26 October 2026" in text
    assert "Warm, plain English" in text
    assert "{{" not in text


def test_a_posting_that_contains_template_slots_changes_nothing():
    filled = fill("Job: {{job}} / Person: {{person}}", job="{{person}}", person="Sam")
    assert filled == "Job: {{person}} / Person: Sam"
    with pytest.raises(ValueError):
        fill("{{a}} {{b}}", a="x")


def test_the_extraction_reply_is_held_to_the_fields():
    pack = get_pack("job")
    extracted = pack.from_extraction(
        {
            "job_title": " Data Analyst ",
            "company_name": "Example Retail",
            "workplace": "mars",
            "location": "Kathmandu",
            "description_markdown": "x" * 200_000,
        }
    )
    assert extracted.title == "Data Analyst" and extracted.issuer_name == "Example Retail"
    assert extracted.attributes["workplace"] == ""
    assert len(extracted.attributes["description_markdown"]) == 100_000
    schema = pack.extraction_schema()
    assert set(schema["required"]) == set(schema["properties"])


def test_every_installed_pack_is_complete():
    for key, pack in all_packs().items():
        assert pack.key == key
        assert pack.pipeline.stages and pack.document_types and pack.profile_kinds
        for spec in pack.document_types:
            if spec.generatable:
                assert spec.prompt and pack.prompt_template(spec.prompt)
        row = pack.registry_row()
        assert row["profile_schema"]["type"] == "object"


def test_form_values_from_a_profile():
    from apply.packs.base import ProfileInput

    values = get_pack("job").form_values(
        ProfileInput(
            name="Backend",
            summary="",
            attributes={
                "full_name": "Sam Bahadur Rai",
                "email": "sam@example.com",
                "links": [
                    {"label": "Site", "url": "https://sam.example.com"},
                    {"label": "", "url": "https://github.com/example"},
                    {"label": "Network profile", "url": "https://linkedin.com/in/example"},
                    {"label": "", "url": "https://other.example"},
                ],
                "experience": [
                    {"title": "Engineer", "organisation": "Old Co", "end": "2020"},
                    {"title": "Lead", "organisation": "Now Co", "end": ""},
                ],
            },
        )
    )
    assert values == {
        "full_name": "Sam Bahadur Rai",
        "first_name": "Sam",
        "last_name": "Bahadur Rai",
        "email": "sam@example.com",
        "website": "https://sam.example.com",
        "github": "https://github.com/example",
        "linkedin": "https://linkedin.com/in/example",
        "current_company": "Now Co",
        "current_title": "Lead",
        "past_employers": "Old Co\nNow Co",
    }
    assert get_pack("job").form_values(ProfileInput(name="x", summary="", attributes={})) == {}
