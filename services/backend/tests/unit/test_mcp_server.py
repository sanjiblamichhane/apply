"""`apply mcp`: its tools over a faked apply API. What an agent sees, what it can't, and how errors read."""

import json

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from apply import mcp_server

SECRET = "apl_" + "a" * 43
OPP = {
    "id": "01OPP",
    "pack": "job",
    "title": "Backend Engineer",
    "issuer_name": "Himal",
    "source_url": "https://jobs.example.com/himal/1",
    "apply_url": None,
    "deadline": None,
    "status": "open",
    "attributes": {"description": "Design APIs."},
    "extraction": {"status": "ready", "method": "json_ld", "error_code": None, "edited": False},
}
APP = {
    "id": "01APP",
    "opportunity": OPP,
    "profile_id": "01PRO",
    "pipeline_id": "01PIP",
    "stage": {"id": "01STG", "code": "new", "category": "active"},
    "current_documents": [],
    "submitted_at": None,
    "notes": "",
}


def doc(id_: str, status: str = "ready", active: bool = True, created: str = "2026-11-01T00:00:00Z") -> dict:
    return {
        "id": id_,
        "application_id": "01APP",
        "document_type": "resume",
        "status": status,
        "error_code": None,
        "version": 1,
        "is_active": active,
        "content_markdown": f"# Resume {id_}",
        "claim_warnings": [
            {"id": "w1", "kind": "confirm", "quote": "10 years", "reason": "Not in the profile", "resolved": None},
            {"id": "w2", "kind": "number", "quote": "5 teams", "reason": "Checked", "resolved": "kept"},
        ],
        "reviewed_at": None,
        "created_at": created,
    }


class FakeApi:
    """apply's API as far as the tools go: answers by method and path, and keeps what was asked."""

    def __init__(self):
        self.seen: list[httpx.Request] = []
        self.answers: dict[tuple[str, str], tuple[int, object]] = {}

    def on(self, method: str, path: str, status: int, body: object) -> None:
        self.answers[(method, "/api/v1" + path)] = (status, body)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        status, body = self.answers.get((request.method, request.url.path), (404, {"code": "NOT_FOUND"}))
        return httpx.Response(status, json=body)


@pytest.fixture
def api():
    return FakeApi()


@pytest.fixture
def server(api):
    http = httpx.AsyncClient(transport=httpx.MockTransport(api), base_url="http://apply.test")
    http.headers["Authorization"] = f"Bearer {SECRET}"
    return mcp_server.build(http)


async def call(server, name: str, **arguments) -> dict:
    return (await server.call_tool(name, arguments)).structured_content


async def test_the_tools_say_apply_drafts_and_the_person_submits(server):
    tools = {t.name: t for t in await server.list_tools()}
    assert set(tools) == {
        "who_am_i",
        "list_applications",
        "add_opportunity",
        "find_application_by_url",
        "get_application",
        "get_profile",
        "write_document",
        "get_document",
    }
    assert not any("submit" in name for name in tools)  # apply never submits, and neither does an agent
    assert all(t.description for t in tools.values())
    readers = {n for n, t in tools.items() if t.annotations.read_only_hint}
    assert readers == set(tools) - {"add_opportunity", "write_document"}
    assert "never submits" in server.instructions


async def test_who_am_i_checks_the_token(server, api):
    token = {"name": "Claude", "kind": "agent", "scopes": ["applications:read"], "expires_at": None, "prefix": "x"}
    api.on("GET", "/tokens/current", 200, {"email": "sam@example.com", "locale": "ne", "token": token})
    me = await call(server, "who_am_i")
    assert me["email"] == "sam@example.com" and me["token"]["kind"] == "agent" and "prefix" not in me["token"]
    assert api.seen[0].headers["authorization"] == f"Bearer {SECRET}"


async def test_list_applications_passes_only_the_filters_given(server, api):
    api.on("GET", "/applications", 200, {"items": [APP], "next_cursor": "01NEXT"})
    found = await call(server, "list_applications", stage="new")
    assert found["next_cursor"] == "01NEXT"
    [brief] = found["applications"]
    assert brief["id"] == "01APP" and brief["title"] == "Backend Engineer" and brief["stage"] == "new"
    assert brief["apply_url"] == OPP["source_url"]
    assert dict(api.seen[0].url.params) == {"stage": "new", "limit": "50"}


async def test_add_opportunity_tracks_it_and_starts_an_application(server, api):
    api.on("POST", "/opportunities", 201, OPP)
    api.on("POST", "/applications", 201, APP)
    added = await call(server, "add_opportunity", url=OPP["source_url"], notes="Looks good")
    assert added["new"] and added["application"]["id"] == "01APP" and added["note"] == ""
    assert json.loads(api.seen[0].content) == {"pack": "job", "url": OPP["source_url"], "text": None}
    assert json.loads(api.seen[1].content) == {"opportunity_id": "01OPP", "notes": "Looks good"}


async def test_add_opportunity_again_gives_the_application_already_there(server, api):
    api.on("POST", "/opportunities", 200, OPP)
    api.on("POST", "/applications", 409, {"code": "APPLICATION_EXISTS", "application_id": "01APP"})
    api.on("GET", "/applications/01APP", 200, APP)
    added = await call(server, "add_opportunity", text="Backend Engineer at Himal")
    assert not added["new"] and added["application"]["id"] == "01APP"


async def test_add_opportunity_needs_a_link_or_the_text(server, api):
    for arguments in ({}, {"url": "https://a.b/c", "text": "Engineer"}):
        with pytest.raises(ToolError, match="url or its text"):
            await server.call_tool("add_opportunity", arguments)
    assert api.seen == []


async def test_find_application_by_url(server, api):
    assert await call(server, "find_application_by_url", url="https://a.b/c") == {"found": False}
    api.on("GET", "/applications/by-url", 200, {"opportunity": OPP, "application": APP})
    found = await call(server, "find_application_by_url", url=OPP["source_url"])
    assert found["found"] and found["application"]["id"] == "01APP"
    assert found["opportunity"]["details"] == {"description": "Design APIs."}


async def test_get_application_leaves_private_answers_out(server, api):
    answers = [
        {"question": {"en": "Gender", "ne": "लिङ्ग"}, "answer": "decline", "is_sensitive": True},
        {"question": {"en": "Notice period", "ne": "सूचना अवधि"}, "answer": "Two weeks", "is_sensitive": False},
    ]
    documents = [
        {"document_id": "01DOC", "document_type": "resume", "version": 2, "reviewed": False, "open_warnings": 1}
    ]
    sheet = {"application": APP, "opportunity": OPP, "values": {"email": "sam@example.com"}, "answers": answers}
    api.on("GET", "/applications/01APP/fill", 200, {**sheet, "documents": documents})
    got = await call(server, "get_application", application_id="01APP")
    assert got["form_values"] == {"email": "sam@example.com"}
    assert got["answers"] == [
        {"question": "Gender", "answer": mcp_server.PRIVATE},
        {"question": "Notice period", "answer": "Two weeks"},
    ]
    assert "decline" not in json.dumps(got)
    assert got["documents"][0]["id"] == "01DOC" and got["documents"][0]["claims_to_check"] == 1


async def test_get_profile_leaves_private_values_out(server, api):
    profile = {"id": "01PRO", "pack": "job", "name": "Sam Rai", "is_default": True}
    items = [
        {"label": {"en": "Email"}, "value": "sam@example.com", "sensitive": False},
        {"label": {"en": "Ethnicity"}, "value": "Prefer to say", "sensitive": True},
    ]
    tabs = [{"key": "basics", "label": {"en": "Basics"}, "groups": [{"title": "", "items": items}]}]
    api.on("GET", "/copy-sheet", 200, {"profile": profile, "profiles": [profile], "tabs": tabs})
    got = await call(server, "get_profile")
    assert got["profile"]["name"] == "Sam Rai" and got["other_profiles"] == []
    assert got["sections"] == [
        {
            "section": "Basics",
            "entries": [{"title": "", "values": {"Email": "sam@example.com", "Ethnicity": mcp_server.PRIVATE}}],
        }
    ]
    assert api.seen[0].url.params.get("pack") is None


async def test_write_document_asks_for_a_draft(server, api):
    api.on("POST", "/applications/01APP/documents", 202, doc("01NEW", status="pending", active=False))
    got = await call(server, "write_document", application_id="01APP", document_type="cover_letter")
    assert got["status"] == "pending" and "get_document" in got["note"]
    assert json.loads(api.seen[0].content) == {"document_type": "cover_letter"}


async def test_get_document_gives_the_one_in_use_unless_a_newer_one_is_being_written(server, api):
    old, new = doc("01OLD"), doc("01NEW", status="pending", active=False, created="2026-11-02T00:00:00Z")
    api.on("GET", "/applications/01APP/documents", 200, {"items": [old]})
    got = await call(server, "get_document", application_id="01APP")
    assert got["id"] == "01OLD" and got["markdown"] == "# Resume 01OLD" and got["in_use"]
    assert got["claims_to_check"] == [{"quote": "10 years", "reason": "Not in the profile"}]  # not the kept one

    api.on("GET", "/applications/01APP/documents", 200, {"items": [old, new]})
    assert (await call(server, "get_document", application_id="01APP"))["status"] == "pending"

    api.on("GET", "/applications/01APP/documents/01OLD", 200, old)
    assert (await call(server, "get_document", application_id="01APP", document_id="01OLD"))["id"] == "01OLD"

    with pytest.raises(ToolError, match="no cover_letter yet"):
        await server.call_tool("get_document", {"application_id": "01APP", "document_type": "cover_letter"})


async def test_errors_read_plainly(server, api):
    api.on("GET", "/tokens/current", 401, {"code": "TOKEN_INVALID", "detail": "That token is unknown"})
    with pytest.raises(ToolError, match="apply token --kind agent"):
        await server.call_tool("who_am_i", {})
    api.on("POST", "/applications/01APP/documents", 422, {"code": "PROFILE_REQUIRED", "detail": "Add a profile first"})
    with pytest.raises(ToolError, match=r"Add a profile first \(PROFILE_REQUIRED\)"):
        await server.call_tool("write_document", {"application_id": "01APP"})


async def test_apply_not_answering():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(refuse), base_url="http://apply.test")
    with pytest.raises(ToolError, match="apply isn't answering at http://apply.test"):
        await mcp_server.build(http).call_tool("who_am_i", {})


def test_the_token_is_needed_and_sent(monkeypatch, capsys):
    monkeypatch.delenv("APPLY_TOKEN", raising=False)
    assert mcp_server.main() == 2
    assert "apply token --kind agent" in capsys.readouterr().err
    http = mcp_server.client("http://127.0.0.1:8110/", SECRET)
    assert str(http.base_url) == "http://127.0.0.1:8110" and http.headers["authorization"] == f"Bearer {SECRET}"


async def test_ids_are_only_ids_and_answers_only_apis(server, api):
    with pytest.raises(ToolError):
        await server.call_tool("get_application", {"application_id": "../tokens"})
    assert api.seen == []

    def page(request):
        return httpx.Response(200, text="<html>not the API</html>")

    http = httpx.AsyncClient(transport=httpx.MockTransport(page), base_url="http://apply.test")
    with pytest.raises(ToolError, match="isn't apply's API"):
        await mcp_server.build(http).call_tool("who_am_i", {})
