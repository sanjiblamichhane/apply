"""
``apply mcp``: an MCP server on stdio, so an AI agent (Claude Desktop, Claude Code, Cursor, …) can use a person's apply.

- It talks to apply's HTTP API, never the database, with a personal API token of kind "agent" (``APPLY_TOKEN``).
  ``APPLY_URL`` is the API: by default http://127.0.0.1:8110, which is also its address inside the apply-api container.
- An agent token reads applications and profiles, tracks new opportunities and asks for documents to be written. It
  can't record a submission, change a profile or touch the account: apply drafts and fills; the person reviews and
  submits.
- Sensitive answers and values (equal-opportunity questions) are left out: they go into a form, never to a model.
"""

import asyncio
import logging
import os
import sys
from typing import Annotated, Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

DEFAULT_URL = "http://127.0.0.1:8110"
API = "/api/v1"
PRIVATE = "(private: the person fills this in)"

INSTRUCTIONS = """\
apply is the person's own workspace for jobs and other opportunities they apply for. With these tools you can track a
posting, read their applications, profile and saved answers, and have apply write a draft resume or cover letter.
apply drafts and fills; it never submits, and neither do you: the person reviews everything and submits it themselves.
Private answers (such as equal-opportunity questions) are not shared with you."""

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
DRAFT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

ID = r"^[0-9A-Za-z]{1,40}$"
Id = Annotated[str, Field(description="An id from another tool's answer", pattern=ID)]
ProfileId = Annotated[str | None, Field(description="A profile's id (default: the pack's default)", pattern=ID)]
DocumentId = Annotated[str | None, Field(description="Its id (default: the one in use of document_type)", pattern=ID)]


class Api:
    """apply's HTTP API, as the token's owner. An error answer becomes a ToolError the agent can read."""

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def call(self, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
        try:
            response = await self.http.request(method, API + path, **kwargs)
        except httpx.HTTPError as exc:
            raise ToolError(f"apply isn't answering at {self.http.base_url} ({type(exc).__name__})") from exc
        try:
            body = response.json() if response.content else None
        except ValueError as exc:
            raise ToolError(f"{self.http.base_url} isn't apply's API (it answered {response.status_code})") from exc
        return response.status_code, body

    async def get(self, path: str, **params: Any) -> Any:
        status, body = await self.call("GET", path, params={k: v for k, v in params.items() if v is not None})
        return ok(status, body)

    async def post(self, path: str, json: dict[str, Any]) -> Any:
        return ok(*await self.call("POST", path, json=json))


def ok(status: int, body: Any) -> Any:
    if status < 400:
        return body
    raise ToolError(problem(status, body))


def problem(status: int, body: Any) -> str:
    code = body.get("code", "") if isinstance(body, dict) else ""
    if status == 401:
        return "The token is unknown, revoked or expired. Make a new one: apply token --kind agent (TOKEN_INVALID)"
    detail = (body.get("detail") or body.get("title")) if isinstance(body, dict) else ""
    return f"{detail or f'apply answered {status}'} ({code or status})"


def en(label: Any) -> str:
    """A label in English (apply's labels are {"en": …, "ne": …})."""
    return label.get("en", "") if isinstance(label, dict) else str(label or "")


def application_brief(app: dict[str, Any]) -> dict[str, Any]:
    opp = app["opportunity"]
    return {
        "id": app["id"],
        "title": opp["title"],
        "issuer": opp["issuer_name"],
        "pack": opp["pack"],
        "stage": app["stage"]["code"],
        "submitted_at": app["submitted_at"],
        "deadline": opp["deadline"],
        "apply_url": opp["apply_url"] or opp["source_url"],
        "opportunity_id": opp["id"],
        "details_read": opp["extraction"]["status"] != "pending",
        "documents": app["current_documents"],
        "notes": app["notes"],
    }


def opportunity_details(opp: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": opp["id"],
        "pack": opp["pack"],
        "title": opp["title"],
        "issuer": opp["issuer_name"],
        "status": opp["status"],
        "deadline": opp["deadline"],
        "source_url": opp["source_url"],
        "apply_url": opp["apply_url"],
        "details_read": opp["extraction"]["status"] != "pending",
        "details": opp["attributes"],
    }


def document_out(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["id"],
        "application_id": doc["application_id"],
        "document_type": doc["document_type"],
        "status": doc["status"],
        "error_code": doc["error_code"],
        "version": doc["version"],
        "in_use": doc["is_active"],
        "reviewed": doc["reviewed_at"] is not None,
        "claims_to_check": [
            {"quote": w["quote"], "reason": w["reason"]} for w in doc["claim_warnings"] if not w.get("resolved")
        ],
        "markdown": doc["content_markdown"],
    }


def build(http: httpx.AsyncClient) -> MCPServer:
    """The server and its tools, over ``http`` (its base_url the API, its headers the token)."""
    api = Api(http)
    server = MCPServer("apply", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ)
    async def who_am_i() -> dict[str, Any]:
        """Check the connection to apply: whose apply this is, their language, and what the token may do."""
        me = await api.get("/tokens/current")
        token = me.get("token") or {}
        return {
            "email": me["email"],
            "locale": me["locale"],
            "web_app": me.get("web_url"),
            "token": {k: token.get(k) for k in ("name", "kind", "scopes", "expires_at")},
        }

    @server.tool(annotations=READ)
    async def list_applications(
        stage: Annotated[str | None, Field(description="Only this stage, like new or in_progress")] = None,
        pack: Annotated[str | None, Field(description="Only this kind: job, grant, tender, contract")] = None,
        limit: Annotated[int, Field(ge=1, le=200)] = 50,
        after: Annotated[str | None, Field(description="next_cursor from the last answer, for more")] = None,
    ) -> dict[str, Any]:
        """The person's applications, newest first: what each is for, its stage and its documents."""
        found = await api.get("/applications", stage=stage, pack=pack, limit=limit, after=after)
        return {"applications": [application_brief(a) for a in found["items"]], "next_cursor": found["next_cursor"]}

    @server.tool(annotations=DRAFT)
    async def add_opportunity(
        url: Annotated[str | None, Field(description="The posting's link", max_length=2048)] = None,
        text: Annotated[str | None, Field(description="Or the posting's text", max_length=100_000)] = None,
        pack: Annotated[str, Field(description="What it is: job (default), grant, tender, contract")] = "job",
        notes: Annotated[str, Field(description="A note for the person", max_length=2000)] = "",
    ) -> dict[str, Any]:
        """
        Track a job (or another opportunity) in apply from its link or its text, and start an application for it.
        Nothing is sent anywhere: the person reviews it and applies themselves. Pasting the same one again gives
        the application already there.
        """
        if bool(url) == bool(text):
            raise ToolError("Give the posting's url or its text (one of the two)")
        opp = await api.post("/opportunities", {"pack": pack, "url": url, "text": text})
        status, app = await api.call("POST", "/applications", json={"opportunity_id": opp["id"], "notes": notes})
        new = status == 201
        if status == 409 and isinstance(app, dict) and app.get("application_id"):
            app = await api.get(f"/applications/{app['application_id']}")
        else:
            app = ok(status, app)
        return {
            "new": new,
            "application": application_brief(app),
            "note": "" if app["opportunity"]["extraction"]["status"] != "pending" else "apply is still reading it",
        }

    @server.tool(annotations=READ)
    async def find_application_by_url(
        url: Annotated[str, Field(description="A posting's link, or its application form's", max_length=2048)],
    ) -> dict[str, Any]:
        """Whether apply already tracks the posting at this link, and its application if there is one."""
        status, found = await api.call("GET", "/applications/by-url", params={"url": url})
        if status == 404:
            return {"found": False}
        found = ok(status, found)
        app = found["application"]
        return {
            "found": True,
            "opportunity": opportunity_details(found["opportunity"]),
            "application": application_brief(app) if app else None,
        }

    @server.tool(annotations=READ)
    async def get_application(application_id: Id) -> dict[str, Any]:
        """
        Everything for one application: the posting's details, the values for its form (from the profile), the
        saved answers to common questions, and the documents ready for it. Private answers are left out.
        """
        sheet = await api.get(f"/applications/{application_id}/fill")
        return {
            "application": application_brief(sheet["application"]),
            "opportunity": opportunity_details(sheet["opportunity"]),
            "form_values": sheet["values"],
            "answers": [
                {"question": en(a["question"]), "answer": PRIVATE if a["is_sensitive"] else a["answer"]}
                for a in sheet["answers"]
            ],
            "documents": [
                {
                    "id": d["document_id"],
                    "document_type": d["document_type"],
                    "version": d["version"],
                    "reviewed": d["reviewed"],
                    "claims_to_check": d["open_warnings"],
                }
                for d in sheet["documents"]
            ],
        }

    @server.tool(annotations=READ)
    async def get_profile(
        profile_id: ProfileId = None,
        pack: Annotated[str | None, Field(description="job (default), grant, tender, contract")] = None,
    ) -> dict[str, Any]:
        """The person's profile, section by section, each value as they'd paste it. Private values are left out."""
        sheet = await api.get("/copy-sheet", profile_id=profile_id, pack=pack)
        return {
            "profile": sheet["profile"],
            "other_profiles": [p for p in sheet["profiles"] if p["id"] != (sheet["profile"] or {}).get("id")],
            "sections": [
                {
                    "section": en(tab["label"]),
                    "entries": [
                        {
                            "title": group["title"],
                            "values": {
                                en(i["label"]): PRIVATE if i["sensitive"] else i["value"] for i in group["items"]
                            },
                        }
                        for group in tab["groups"]
                    ],
                }
                for tab in sheet["tabs"]
            ],
        }

    @server.tool(annotations=DRAFT)
    async def write_document(
        application_id: Id,
        document_type: Annotated[str, Field(description="resume or cover_letter (for a job)")] = "resume",
    ) -> dict[str, Any]:
        """
        Have apply write a draft document for an application, from the person's profile and the posting, on their
        own model. It takes a while: check it with get_document. The person reviews the draft before using it.
        """
        doc = await api.post(f"/applications/{application_id}/documents", {"document_type": document_type})
        return {**document_out(doc), "note": "Being written: ask get_document for it in a minute or two"}

    @server.tool(annotations=READ)
    async def get_document(
        application_id: Id,
        document_id: DocumentId = None,
        document_type: Annotated[str, Field(description="resume or cover_letter (for a job)")] = "resume",
    ) -> dict[str, Any]:
        """
        A document's text (Markdown) and status: pending while it's written, then ready. claims_to_check are lines
        apply couldn't match to the profile, for the person to check.
        """
        if document_id:
            return document_out(await api.get(f"/applications/{application_id}/documents/{document_id}"))
        docs = (await api.get(f"/applications/{application_id}/documents"))["items"]
        mine = [d for d in docs if d["document_type"] == document_type]
        if not mine:
            raise ToolError(f"This application has no {document_type} yet: write_document makes one")
        in_use = [d for d in mine if d["is_active"]]
        latest = max(mine, key=lambda d: d["created_at"])
        # The one in use, unless a newer one is being written or failed: then that, so the agent sees it.
        return document_out(in_use[0] if in_use and latest["status"] == "ready" else latest)

    return server


def client(url: str, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=url.rstrip("/"),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "apply-mcp"},
        timeout=httpx.Timeout(60.0, connect=5.0),
    )


def main() -> int:
    token = os.environ.get("APPLY_TOKEN", "").strip()
    if not token:
        print("Set APPLY_TOKEN to an agent token. Make one with: apply token --kind agent", file=sys.stderr)
        return 2
    url = os.environ.get("APPLY_URL", "").strip() or DEFAULT_URL
    logging.getLogger("httpx").setLevel(logging.WARNING)

    async def run() -> None:
        async with client(url, token) as http:
            await build(http).run_stdio_async()

    asyncio.run(run())
    return 0
