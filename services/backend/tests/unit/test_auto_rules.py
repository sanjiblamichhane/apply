"""Auto's rules on their own: the same issuer, the owner's day, and what's never answered for someone."""

from datetime import UTC, datetime

from apply.logic import auto
from apply.packs import get_pack
from apply.store.sql.models import User


def test_the_same_issuer_however_it_is_written():
    assert auto.issuer_key("Acme Robotics, Inc.") == auto.issuer_key("acme robotics") == "acmerobotics"
    assert auto.issuer_key("Globex Corporation") == "globex"
    assert auto.issuer_key("Acme") != auto.issuer_key("Acme Robotics")


def test_the_cap_counts_the_owners_own_day():
    user = User(time_zone="Asia/Kathmandu")
    now = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)  # 01:45 on the 27th in Kathmandu
    assert auto.start_of_local_day(user, now) == datetime(2026, 10, 26, 18, 15, tzinfo=UTC)


def test_who_someone_is_is_a_sensitive_question():
    """Security review: the server decides what's sensitive from the form's own words (English, Nepali, Spanish)."""
    rule = get_pack("job").is_sensitive_question
    for label in (
        "How do you describe your gender identity?",
        "Please describe any disability we should know about",
        "What is your date of birth?",
        "Your pronouns",
        "Do you have any criminal convictions?",
        "तपाईंको जात",
        "Race or ethnicity (equal-opportunity question)",
        "¿Con qué género se identifica?",
        "¿Tiene alguna discapacidad?",
        "Fecha de nacimiento",
        "Número de DNI",
        "¿Tiene antecedentes penales?",
    ):
        assert rule(label), label
    for label in (
        "Why do you want to work here?",
        "Describe a project you're proud of",
        "Cover letter",
        "¿Por qué quiere trabajar aquí?",
        "Describa un proyecto del que esté orgulloso",
        "Carta de presentación",
    ):
        assert not rule(label), label
    assert get_pack("tender").is_sensitive_question("Gender pay gap report")  # cautious in every pack
