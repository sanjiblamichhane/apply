"""Reviewing documents, their PDFs, saved answers, the Application kit and submissions (routes under /api/v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from apply.logic import answers, documents, files, kit, review, templates
from apply.packs import DEFAULT_PACK
from apply.store.sql.models import User

from . import schemas as s
from .deps import Reader, Rt, Submitter, current_user, token_of

Owner = Annotated[User, Depends(current_user)]
reviewing = APIRouter()
DOC = "/applications/{application_id}/documents/{document_id}"


@reviewing.put(f"{DOC}/content", tags=["review"], status_code=status.HTTP_201_CREATED)
async def edit_document(
    application_id: str, document_id: str, body: s.DocumentContent, rt: Rt, user: Owner
) -> s.DocumentOut:
    """Your own wording: saved as a new version (the one in use) and checked again."""
    async with rt.db.transaction() as session:
        doc = await review.edit(session, user.id, application_id, document_id, body.content_markdown)
        return s.DocumentOut.model_validate(doc)


@reviewing.post(f"{DOC}/warnings/{{warning_id}}", tags=["review"])
async def resolve_warning(
    application_id: str, document_id: str, warning_id: str, body: s.WarningResolution, rt: Rt, user: Owner
) -> s.DocumentOut:
    """ "It's true" (kept), "It's wrong" (with what's true instead, or empty to take it out), or open again."""
    async with rt.db.transaction() as session:
        doc = await review.resolve(
            session, user.id, application_id, document_id, warning_id, body.resolution, body.correction
        )
        return s.DocumentOut.model_validate(doc)


@reviewing.post(
    f"{DOC}/rewrite",
    tags=["review"],
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"model": s.DocumentOut, "description": "One is already being written: that one"}},
)
async def rewrite_document(
    application_id: str, document_id: str, body: s.Rewrite, response: Response, rt: Rt, user: Owner
) -> s.DocumentOut:
    """
    Write this document again from this version, with the corrections on its warnings and the notes. 202 with the
    pending version; 409 NOTHING_TO_REWRITE with neither.
    """
    async with rt.db.transaction() as session:
        row, queued = await documents.rewrite(session, user.id, application_id, document_id, body.notes)
        if not queued:
            response.status_code = status.HTTP_200_OK
        return s.DocumentOut.model_validate(row)


@reviewing.post(f"{DOC}/review", tags=["review"])
async def mark_reviewed(application_id: str, document_id: str, body: s.Reviewed, rt: Rt, user: Owner) -> s.DocumentOut:
    async with rt.db.transaction() as session:
        doc = await review.mark_reviewed(session, user.id, application_id, document_id, body.reviewed)
        return s.DocumentOut.model_validate(doc)


@reviewing.post(f"{DOC}/check", tags=["review"], status_code=status.HTTP_202_ACCEPTED)
async def check_document(application_id: str, document_id: str, rt: Rt, user: Owner) -> s.DocumentOut:
    async with rt.db.transaction() as session:
        return s.DocumentOut.model_validate(await review.check_again(session, user.id, application_id, document_id))


FILES = {
    "pdf": ("application/pdf", "The PDF"),
    "html": ("text/html", "The page"),
    "docx": (files.DOCX, "The Word file"),
}
# A document's page is shown in a sandboxed frame and opened on its own: it runs nothing and fetches nothing.
PAGE_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; sandbox"


async def _file(application_id: str, document_id: str, kind: str, download: bool, rt: Rt, user: User) -> Response:
    async with rt.db.transaction() as session:
        found = await review.rendered(session, user.id, application_id, document_id, kind)
        data = await files.get(rt, session, found) if found else None
    if data is None:
        raise review.pending()
    headers = {
        "Content-Disposition": f'{"attachment" if download else "inline"}; filename="{document_id}.{kind}"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if kind == "html":
        headers["Content-Security-Policy"] = PAGE_CSP
    return Response(data, media_type=FILES[kind][0], headers=headers)


@reviewing.get(
    f"{DOC}/pdf",
    tags=["review"],
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "The PDF"}},
)
async def document_pdf(application_id: str, document_id: str, rt: Rt, user: Reader, download: bool = False) -> Response:
    """The version in its template, printed to a tagged PDF/UA-1. 409 RENDER_PENDING (Retry-After) while it's made."""
    return await _file(application_id, document_id, "pdf", download, rt, user)


@reviewing.get(
    f"{DOC}/html",
    tags=["review"],
    response_class=Response,
    responses={200: {"content": {"text/html": {}}, "description": "The page"}},
)
async def document_html(
    application_id: str, document_id: str, rt: Rt, user: Reader, download: bool = False
) -> Response:
    """The version in its template, as the page (what's previewed). 409 RENDER_PENDING while it's made."""
    return await _file(application_id, document_id, "html", download, rt, user)


@reviewing.get(
    f"{DOC}/docx",
    tags=["review"],
    response_class=Response,
    responses={200: {"content": {files.DOCX: {}}, "description": "The Word file"}},
)
async def document_docx(application_id: str, document_id: str, rt: Rt, user: Reader, download: bool = True) -> Response:
    """The version as a Word file (.docx), to edit in a word processor. 409 RENDER_PENDING while it's made."""
    return await _file(application_id, document_id, "docx", download, rt, user)


def _template_out(kind: s.TemplateKind, html: str, found) -> s.TemplateOut:
    return s.TemplateOut(
        kind=kind,
        custom=found is not None,
        filename=found.filename if found else f"{kind}.html",
        html=html,
        preview_html=templates.preview(html, kind),
        updated_at=found.updated_at if found else None,
    )


@reviewing.get("/templates/{kind}", tags=["templates"])
async def get_template(kind: s.TemplateKind, rt: Rt, user: Owner) -> s.TemplateOut:
    """The template your documents of this kind are made in (yours, or the default), and a sample in it."""
    async with rt.db.transaction() as session:
        found = await templates.mine(session, user.id, kind)
        return _template_out(kind, found.html if found else templates.default_template(kind), found)


@reviewing.get("/templates/{kind}/default", tags=["templates"])
async def default_template(kind: s.TemplateKind, user: Owner) -> s.TemplateOut:
    """The default, to start your own from."""
    return _template_out(kind, templates.default_template(kind), None)


@reviewing.post("/templates/{kind}/check", tags=["templates"])
async def check_template(kind: s.TemplateKind, body: s.TemplateIn, user: Owner) -> s.TemplateCheck:
    """What would stop this template being kept (nothing: it may be), and a sample in it, without keeping it."""
    problems = templates.check(body.html, kind)
    unfillable = any(p.code == "placeholder" for p in problems)
    return s.TemplateCheck(
        problems=[s.TemplateProblem(code=p.code, message=p.message, wcag=p.wcag) for p in problems],
        preview_html="" if unfillable else templates.preview(body.html, kind),
    )


@reviewing.put("/templates/{kind}", tags=["templates"])
async def save_template(kind: s.TemplateKind, body: s.TemplateIn, rt: Rt, user: Owner) -> s.TemplateOut:
    """Your own template, kept if it passes every check (422 TEMPLATE_PROBLEMS with the problems if not)."""
    async with rt.db.transaction() as session:
        found = await templates.save(session, user.id, kind, body.html, body.filename)
        return _template_out(kind, found.html, found)


@reviewing.delete("/templates/{kind}", tags=["templates"], status_code=status.HTTP_204_NO_CONTENT)
async def reset_template(kind: s.TemplateKind, rt: Rt, user: Owner) -> None:
    """Back to the default."""
    async with rt.db.transaction() as session:
        await templates.reset(session, user.id, kind)


@reviewing.get("/answers", tags=["answers"])
async def list_answers(rt: Rt, user: Owner, pack: str = DEFAULT_PACK) -> s.Answers:
    async with rt.db.transaction() as session:
        return s.Answers(items=[s.AnswerOut.model_validate(a) for a in await answers.list_(session, user.id, pack)])


@reviewing.post("/answers/defaults", tags=["answers"])
async def add_default_answers(rt: Rt, user: Owner, pack: str = DEFAULT_PACK) -> s.AddedDefaults:
    """The pack's common questions you don't have yet (sensitive ones start as "Decline to answer")."""
    async with rt.db.transaction() as session:
        return s.AddedDefaults(added=await answers.add_defaults(session, user.id, pack))


@reviewing.post("/answers", tags=["answers"], status_code=status.HTTP_201_CREATED)
async def create_answer(body: s.NewAnswer, rt: Rt, user: Owner) -> s.AnswerOut:
    async with rt.db.transaction() as session:
        return s.AnswerOut.model_validate(await answers.create(session, user.id, **body.model_dump()))


@reviewing.patch("/answers/{answer_id}", tags=["answers"])
async def update_answer(answer_id: str, body: s.AnswerChanges, rt: Rt, user: Owner) -> s.AnswerOut:
    async with rt.db.transaction() as session:
        changes = body.model_dump(exclude_unset=True)
        return s.AnswerOut.model_validate(await answers.update(session, user.id, answer_id, changes))


@reviewing.delete("/answers/{answer_id}", tags=["answers"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(answer_id: str, rt: Rt, user: Owner) -> None:
    async with rt.db.transaction() as session:
        await answers.delete(session, user.id, answer_id)


@reviewing.get("/applications/{application_id}/kit", tags=["kit"])
async def application_kit(application_id: str, rt: Rt, user: Owner) -> s.Kit:
    """Everything to apply by hand: where, which documents (and their warnings), the answers."""
    async with rt.db.transaction() as session:
        found = await kit.kit(session, user.id, application_id)
        return s.Kit(
            application=s.ApplicationOut.model_validate(found["application"]),
            apply_url=found["apply_url"],
            documents=[
                s.KitDocument(
                    document=s.DocumentOut.model_validate(d["document"]),
                    label=s.Label(**d["label"]),
                    open_warnings=d["open_warnings"],
                )
                for d in found["documents"]
            ],
            answers=[s.AnswerOut.model_validate(a) for a in found["answers"]],
            submissions=[s.SubmissionOut.model_validate(x) for x in found["submissions"]],
        )


@reviewing.post(
    "/applications/{application_id}/submissions",
    tags=["kit"],
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": s.SubmissionOut, "description": "Recorded already (a reloaded confirmation page)"}},
)
async def submit_application(
    application_id: str, body: s.NewSubmission, request: Request, response: Response, rt: Rt, user: Submitter
) -> s.SubmissionOut:
    """
    "I've submitted it": what went out is recorded, and the application moves on. With a token, the channel is
    the token's (the extension), and the same submission again within the undo window is answered with the first.
    """
    token = token_of(request)
    details = {}
    if body.confirmation_url:
        details["confirmation_url"] = body.confirmation_url
    if body.filled:
        details["filled"] = body.filled.model_dump()
    async with rt.db.transaction() as session:
        submission, created = await kit.submit(
            session,
            user.id,
            application_id,
            note=body.note,
            channel=token.kind if token else "manual",
            details=details,
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return s.SubmissionOut.model_validate(submission)


@reviewing.post("/submissions/{submission_id}/undo", tags=["kit"])
async def undo_submission(submission_id: str, rt: Rt, user: Submitter) -> s.SubmissionOut:
    """Undo, within 10 minutes (UNDO_TOO_LATE after)."""
    async with rt.db.transaction() as session:
        return s.SubmissionOut.model_validate(await kit.undo(session, user.id, submission_id))
