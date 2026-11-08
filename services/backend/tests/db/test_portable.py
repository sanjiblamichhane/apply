"""apply-export/1: export one owner, import into another, and nothing is lost; importing again adds nothing."""

import pytest
from sqlalchemy import select

from apply.libs.render import default_template
from apply.logic import applications, documents, opportunities, portable, profiles
from apply.logic.portable import PortableExport
from apply.store.sql.models import ApplicationDocument, DocumentTemplate
from apply.store.sql.repo import users
from tests.conftest import add_account

PROFILE = {
    "full_name": "Sam Rai",
    "skills": ["Python"],
    "experience": [{"title": "Backend Engineer", "organisation": "Himal Tech", "highlights": ["APIs"]}],
}


def nonzero(counts: dict[str, int]) -> dict[str, int]:
    return {k: v for k, v in counts.items() if v}


@pytest.fixture
async def owners(rt):
    await add_account(rt, "a@example.com", "a long enough password")
    await add_account(rt, "b@example.com", "b long enough password")
    async with rt.db.transaction() as session:
        return (await users.by_email(session, "a@example.com")).id, (await users.by_email(session, "b@example.com")).id


async def fill(rt, owner: str) -> None:
    async with rt.db.transaction() as session:
        profile = await profiles.create(
            session,
            owner,
            pack="job",
            kind="individual",
            name="Backend",
            summary="S",
            attributes=PROFILE,
            tone_instructions="Plain",
            is_default=True,
        )
    opp, _ = await opportunities.paste(rt, owner, pack_key="job", url=None, text="Engineer at Acme\nPython")
    async with rt.db.transaction() as session:
        app = await applications.create(session, owner, opportunity_id=opp.id, profile_id=profile.id, notes="N")
        await applications.move(session, owner, app.id, stage_code="interview", note="Call on Friday")
        for version in (1, 2):
            session.add(
                ApplicationDocument(
                    owner_id=owner,
                    application_id=app.id,
                    profile_id=profile.id,
                    document_type="resume",
                    status="ready",
                    version=version,
                    is_active=version == 2,
                    content_markdown=f"# Resume v{version}",
                )
            )


async def test_export_then_import_into_another_owner(rt, owners):
    a, b = owners
    await fill(rt, a)
    async with rt.db.transaction() as session:
        exported = await portable.export(session, a)
    data = PortableExport.model_validate_json(exported.model_dump_json())  # through JSON, as a file would
    async with rt.db.transaction() as session:
        report = await portable.import_(session, b, data)
    assert nonzero(report.created) == {"profiles": 1, "opportunities": 1, "applications": 1, "documents": 2}
    assert report.problems == []

    async with rt.db.transaction() as session:
        [profile], _ = await profiles.list_(session, b, pack="job", after=None, limit=10)
        assert profile.attributes["experience"][0]["organisation"] == "Himal Tech" and profile.is_default
        [app], _ = await applications.list_(session, b, pack=None, stage_code=None, after=None, limit=10)
        assert app.stage.code == "interview" and app.notes == "N" and app.profile_id == profile.id
        history = await applications.history(session, b, app.id)
        assert [h.stage.code for h in history] == ["interview", "new"] and history[0].note == "Call on Friday"
        docs = await documents.list_(session, b, app.id)
        assert [(d.version, d.is_active, d.content_markdown, d.source) for d in docs] == [
            (2, True, "# Resume v2", "imported"),
            (1, False, "# Resume v1", "imported"),
        ]

    async with rt.db.transaction() as session:
        again = await portable.import_(session, b, data)
    assert nonzero(again.created) == {}
    assert nonzero(again.already) == {"profiles": 1, "opportunities": 1, "applications": 1, "documents": 2}


async def test_what_doesnt_fit_is_skipped_and_reported(rt, owners):
    a, _ = owners
    data = PortableExport(
        profiles=[
            {"ref": "p1", "name": "X", "attributes": {"shoe_size": 44}},
            {"ref": "p2", "pack": "visa", "name": "Y"},
        ],
        applications=[{"ref": "x1", "opportunity_ref": "missing"}],
    )
    async with rt.db.transaction() as session:
        report = await portable.import_(session, a, data)
    assert report.created["profiles"] == 0 and len(report.problems) == 3


async def test_an_import_is_all_or_nothing(rt, owners):
    a, _ = owners
    data = PortableExport(profiles=[{"ref": "p1", "name": "X"}])
    with pytest.raises(RuntimeError):
        async with rt.db.transaction() as session:
            await portable.import_(session, a, data)
            raise RuntimeError("disk full")
    async with rt.db.transaction() as session:
        from apply.store.sql.models import Profile

        assert (await session.execute(select(Profile))).first() is None


async def test_restoring_into_the_same_account_adds_nothing(rt, owners):
    a, _ = owners
    await fill(rt, a)
    async with rt.db.transaction() as session:
        data = await portable.export(session, a)
    async with rt.db.transaction() as session:
        report = await portable.import_(session, a, data)
    assert sum(report.created.values()) == 0, report


MY_LETTER = default_template("letter").replace("--accent: #1f3864", "--accent: #0b4f2c")


async def test_everything_the_person_made_goes_with_them(rt, owners):
    """Every owned table that holds the person's own work round-trips; the rest are listed as left out on purpose."""
    from datetime import UTC, datetime

    from apply.store.sql.models import Answer, Base, Match, Search, Source, Submission, User

    a, b = owners
    await fill(rt, a)
    async with rt.db.transaction() as session:
        user = await session.get(User, a)
        user.time_zone, user.briefing_hour, user.auto_min_score, user.auto_paused = "Asia/Kathmandu", 6, 90, False
        [app], _ = await applications.list_(session, a, pack=None, stage_code=None, after=None, limit=10)
        [doc] = [d for d in await documents.list_(session, a, app.id) if d.is_active]
        doc.claims_status, doc.reviewed_at = "checked", datetime(2026, 10, 20, tzinfo=UTC)
        doc.claim_warnings = [{"id": "w1", "kind": "number", "quote": "12", "resolved": "kept"}]
        source = Source(owner_id=a, pack="job", kind="board01", name="Acme", config={"board": "acme"})
        session.add(source)
        await session.flush()
        search = Search(
            owner_id=a,
            pack="job",
            name="Python",
            criteria={"keywords": ["python"], "source_ids": [source.id]},
            auto_enabled=True,
        )
        session.add(search)
        await session.flush()
        session.add(
            Match(
                owner_id=a,
                opportunity_id=app.opportunity_id,
                search_ids=[search.id],
                status="tracked",
                score=88,
                score_status="scored",
                score_reasons=["Python"],
                application_id=app.id,
            )
        )
        session.add(
            Answer(
                owner_id=a,
                pack="job",
                key="notice_period",
                question={"en": "Notice?", "ne": "सूचना?"},
                answer="One month",
            )
        )
        session.add(DocumentTemplate(owner_id=a, kind="letter", html=MY_LETTER, filename="mine.html"))
        session.add(
            Submission(
                owner_id=a,
                application_id=app.id,
                channel="auto",
                note="Sent",
                details={"filled": 9, "screenshots": ["01ABC"]},
            )
        )

    async with rt.db.transaction() as session:
        exported = await portable.export(session, a)
    data = PortableExport.model_validate_json(exported.model_dump_json())
    async with rt.db.transaction() as session:
        report = await portable.import_(session, b, data)
    assert report.problems == []
    assert nonzero(report.created) == {
        "profiles": 1,
        "opportunities": 1,
        "applications": 1,
        "documents": 2,
        "submissions": 1,
        "answers": 1,
        "templates": 1,
        "sources": 1,
        "searches": 1,
        "matches": 1,
    }

    async with rt.db.transaction() as session:
        moved = await session.get(User, b)
        assert (moved.time_zone, moved.briefing_hour, moved.auto_min_score) == ("Asia/Kathmandu", 6, 90)
        [app], _ = await applications.list_(session, b, pack=None, stage_code=None, after=None, limit=10)
        [doc] = [d for d in await documents.list_(session, b, app.id) if d.is_active]
        assert doc.claims_status == "checked" and doc.reviewed_at is not None
        assert doc.claim_warnings[0]["resolved"] == "kept"
        [source] = (await session.execute(select(Source).where(Source.owner_id == b))).scalars().all()
        [search] = (await session.execute(select(Search).where(Search.owner_id == b))).scalars().all()
        assert search.criteria["source_ids"] == [source.id]  # pointing at the copy, not the original
        assert search.auto_enabled is False  # Auto is turned on again by hand
        [match] = (await session.execute(select(Match).where(Match.owner_id == b))).scalars().all()
        assert (match.status, match.score, match.search_ids, match.application_id) == (
            "tracked",
            88,
            [search.id],
            app.id,
        )
        [sub] = (await session.execute(select(Submission).where(Submission.owner_id == b))).scalars().all()
        assert sub.channel == "auto" and sub.details == {"filled": 9}  # screenshots stay with Auto's run
        [answer] = (await session.execute(select(Answer).where(Answer.owner_id == b))).scalars().all()
        assert answer.answer == "One month"
        [mine] = (await session.execute(select(DocumentTemplate).where(DocumentTemplate.owner_id == b))).scalars()
        assert (mine.kind, mine.html, mine.filename) == ("letter", MY_LETTER, "mine.html")

    async with rt.db.transaction() as session:
        again = await portable.import_(session, b, data)
    assert nonzero(again.created) == {}

    # A new owned table must be exported, or named here with the reason it isn't.
    exported_tables = {
        "document_templates",
        "profiles",
        "opportunities",
        "applications",
        "stage_history",
        "application_documents",
        "submissions",
        "answers",
        "sources",
        "searches",
        "matches",
    }
    left_out = {
        "sessions": "secrets: sign in again",
        "api_tokens": "secrets: make new ones",
        "briefings": "made again from the rest",
        "rendered_files": "PDFs, made again from the documents",
        "auto_runs": "operational; the outcome is kept as the submission",
        "auto_screenshots": "large images that belong to a run",
        "imports": "the import bookkeeping itself",
        "pipelines": "the pack's, or remade",
        "stages": "the pack's, or remade",
        "packs": "built in, written at start",
        "known_devices": "browsers signed in from: tied to this install's cookies",
        "password_resets": "secrets: ask for a new link",
        "jobs": "the background queue: work in flight, not the person's",
    }
    owned = {t.name for t in Base.metadata.sorted_tables if "owner_id" in t.c}
    assert owned - exported_tables - set(left_out) == set(), "a new table with owner_id isn't in the export"


async def test_an_import_never_turns_auto_back_on(rt, owners):
    from apply.store.sql.models import User

    a, b = owners
    async with rt.db.transaction() as session:
        (await session.get(User, b)).auto_paused = True
        (await session.get(User, a)).auto_paused = False
        exported = await portable.export(session, a)
    async with rt.db.transaction() as session:
        await portable.import_(session, b, exported)
        assert (await session.get(User, b)).auto_paused is True
