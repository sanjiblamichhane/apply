"""Every query is the owner's: one owner never sees or changes another's rows, even with the right id."""

import pytest

from apply.errors import ApplyError, ErrorCode
from apply.logic import applications, documents, opportunities, profiles
from tests.conftest import add_account


@pytest.fixture
async def two_owners(rt):
    from apply.store.sql.repo import users

    await add_account(rt, "a@example.com", "a long enough password")
    await add_account(rt, "b@example.com", "b long enough password")
    async with rt.db.transaction() as session:
        a = await users.by_email(session, "a@example.com")
        b = await users.by_email(session, "b@example.com")
    return a.id, b.id


async def test_another_owners_rows_are_not_found(rt, two_owners):
    a, b = two_owners
    async with rt.db.transaction() as session:
        profile = await profiles.create(
            session,
            a,
            pack="job",
            kind="individual",
            name="A",
            summary="",
            attributes={},
            tone_instructions="",
            is_default=None,
        )
    opp, _ = await opportunities.paste(rt, a, pack_key="job", url=None, text="Engineer at Acme\nPython")
    async with rt.db.transaction() as session:
        app = await applications.create(session, a, opportunity_id=opp.id, profile_id=profile.id)

    checks = [
        (lambda s: profiles.get(s, b, profile.id), ErrorCode.PROFILE_NOT_FOUND),
        (lambda s: profiles.update(s, b, profile.id, {"name": "taken"}), ErrorCode.PROFILE_NOT_FOUND),
        (lambda s: profiles.delete(s, b, profile.id), ErrorCode.PROFILE_NOT_FOUND),
        (lambda s: opportunities.get(s, b, opp.id), ErrorCode.OPPORTUNITY_NOT_FOUND),
        (lambda s: opportunities.update(s, b, opp.id, {"title": "x"}), ErrorCode.OPPORTUNITY_NOT_FOUND),
        (lambda s: applications.get(s, b, app.id), ErrorCode.APPLICATION_NOT_FOUND),
        (lambda s: applications.move(s, b, app.id, stage_code="interview"), ErrorCode.APPLICATION_NOT_FOUND),
        (lambda s: applications.history(s, b, app.id), ErrorCode.APPLICATION_NOT_FOUND),
        (lambda s: applications.create(s, b, opportunity_id=opp.id, profile_id=None), ErrorCode.OPPORTUNITY_NOT_FOUND),
        (
            lambda s: documents.request(s, b, app.id, document_type="resume", profile_id=None),
            ErrorCode.APPLICATION_NOT_FOUND,
        ),
        (lambda s: documents.list_(s, b, app.id), ErrorCode.APPLICATION_NOT_FOUND),
    ]
    for call, code in checks:
        with pytest.raises(ApplyError) as caught:
            async with rt.db.transaction() as session:
                await call(session)
        assert caught.value.code == code
        assert caught.value.status == 404

    # B may not use A's profile for B's own application either.
    opp_b, _ = await opportunities.paste(rt, b, pack_key="job", url=None, text="Designer at Beta\nFigma")
    with pytest.raises(ApplyError) as caught:
        async with rt.db.transaction() as session:
            await applications.create(session, b, opportunity_id=opp_b.id, profile_id=profile.id)
    assert caught.value.code == ErrorCode.PROFILE_NOT_FOUND

    # And A's things are untouched.
    async with rt.db.transaction() as session:
        assert (await profiles.get(session, a, profile.id)).name == "A"
        listed, _ = await opportunities.list_(session, b, pack=None, after=None, limit=50)
        assert [o.id for o in listed] == [opp_b.id]


async def test_the_same_text_is_a_separate_opportunity_for_each_owner(rt, two_owners):
    a, b = two_owners
    first, created_a = await opportunities.paste(rt, a, pack_key="job", url=None, text="Same posting")
    second, created_b = await opportunities.paste(rt, b, pack_key="job", url=None, text="Same posting")
    assert created_a and created_b and first.id != second.id
