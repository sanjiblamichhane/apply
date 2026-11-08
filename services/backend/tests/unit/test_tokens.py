"""Personal API tokens: their shape, scopes, and the URL candidates the extension's lookup compares."""

from datetime import UTC, datetime, timedelta

import pytest

from apply.errors import ApplyError
from apply.logic import fill, tokens
from apply.store.sql.models import ApiToken


def test_scopes_are_known_ordered_and_not_empty():
    assert tokens.clean_scopes(["submissions:write", "applications:read", "applications:read"]) == [
        "applications:read",
        "submissions:write",
    ]
    for bad in ([], ["admin"], ["applications:read", "profiles:write"]):
        with pytest.raises(ApplyError):
            tokens.clean_scopes(bad)


def test_what_looks_like_a_token():
    assert tokens.looks_like_token("apl_" + "a" * 43)
    assert not tokens.looks_like_token("a" * 47)
    assert not tokens.looks_like_token("apl_short")
    assert not tokens.looks_like_token("apl_" + "a" * 200)


def test_usable_until_revoked_or_expired():
    now = datetime.now(UTC)
    assert tokens.usable(ApiToken(expires_at=None, revoked_at=None), now)
    assert tokens.usable(ApiToken(expires_at=now + timedelta(days=1), revoked_at=None), now)
    assert not tokens.usable(ApiToken(expires_at=now - timedelta(seconds=1), revoked_at=None), now)
    assert not tokens.usable(ApiToken(expires_at=None, revoked_at=now), now)


def test_lookup_candidates_are_web_urls_as_given_and_canonical():
    got = fill.candidates(
        ["https://Jobs.Example.com/himal/abc/apply/?utm_source=x", "javascript:alert(1)", "ftp://x", "https://a.b/c"]
    )
    assert got == [
        "https://Jobs.Example.com/himal/abc/apply/?utm_source=x",
        "https://jobs.example.com/himal/abc/apply",
        "https://a.b/c",
    ]
    assert len(fill.candidates([f"https://a.b/{i}" for i in range(50)])) == fill.MAX_URLS


def test_file_names_people_see():
    assert fill.filename("Sam Rai", "Resume") == "Sam Rai – Resume.pdf"
    assert fill.filename("", "Cover letter") == "Cover letter.pdf"
    assert fill.filename('A/B: "C"', "Resume") == "A B C – Resume.pdf"
