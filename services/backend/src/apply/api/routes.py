"""
The HTTP API, /api/v1. Handlers only parse, call logic, and shape the response; rules live in logic/, SQL in
store/. Every route but health and sign-in needs a session; another owner's row is always "not found".
"""

import logging
import time
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, Response, UploadFile, status

from apply import __version__, demo
from apply.errors import Conflict, ErrorCode, NotFound, PermissionDenied, TooManyRequests, Unauthenticated
from apply.i18n import mail_text
from apply.libs import mail
from apply.libs.extract.document import CONTENT_TYPES
from apply.logic import applications, auth, documents, files, fill, model_choice, opportunities, people, profiles
from apply.packs import DEFAULT_PACK, all_packs
from apply.packs import get_pack as find_pack
from apply.packs.base import ACTION_LABELS, CATEGORY_LABELS, PROFILE_KIND_LABELS
from apply.runtime import Runtime
from apply.store.sql.models import User
from apply.store.sql.repo import packs as packs_repo
from apply.store.sql.repo import users as users_repo

from . import schemas as s
from .deps import Reader, Rt, TheOwner, Writer, cookie_name, current_user, device_cookie_name, same_origin

PROBLEM = {"model": s.Problem}  # sent as application/problem+json (app._openapi)

logger = logging.getLogger("apply.api")

api = APIRouter(prefix="/api/v1", dependencies=[Depends(same_origin)], responses={"4XX": PROBLEM, "5XX": PROBLEM})

Owner = Annotated[User, Depends(current_user)]
After = Annotated[str | None, Query(max_length=26)]
Limit = Annotated[int, Query(ge=1, le=200)]


# ─── system ──────────────────────────────────────────────────────────────────


@api.get("/health", tags=["system"])
async def health(rt: Rt) -> s.Health:
    """Liveness, and whether the database and the file bucket answer."""
    try:
        async with rt.db.engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        database = True
    except Exception:
        database = False
    storage = await rt.files.reachable()
    return s.Health(
        status="ok" if database and storage else "degraded", database=database, storage=storage, version=__version__
    )


@api.get("/system/model", tags=["system"])
async def model_status(rt: Rt, _user: Owner) -> s.ModelStatus:
    """Is the model reachable, and are the configured models pulled?"""
    check = await rt.model.check()
    return s.ModelStatus(
        reachable=check.reachable,
        ready=check.ready,
        base_url=check.base_url,
        version=check.version,
        wanted=list(check.wanted),
        installed=list(check.installed),
        missing=list(check.missing),
        num_ctx=check.num_ctx,
    )


def _in_use(current: model_choice.Current) -> s.ModelInUse:
    c = current.choice
    return s.ModelInUse(
        api=c.api,
        base_url=c.base_url,
        model=c.model,
        writing_model=c.writing_model,
        num_ctx=c.num_ctx if c.api == "native" else None,
        source=current.source,
    )


@api.get("/system/models", tags=["system"])
async def models(rt: Rt, _user: Owner) -> s.Models:
    """The model servers on this machine (the configured host, fixed ports), their models, and which is in use."""
    found = await model_choice.find(rt.settings)
    return s.Models(
        current=_in_use(await model_choice.current(rt.db, rt.settings)),
        endpoints=[
            s.EndpointOut(
                api=e.api,
                base_url=e.base_url,
                version=e.version,
                models=[s.FoundModelOut(**m.__dict__) for m in e.models],
            )
            for e in found
        ],
    )


@api.put("/system/model", tags=["system"])
async def choose_model(body: s.ChooseModel, rt: Rt, _user: TheOwner) -> s.ModelChosen:
    """
    Use a model found on this machine, after a short test: a server and model just found, and a usable JSON
    answer from each chosen model. MODEL_NOT_FOUND or MODEL_TEST_FAILED otherwise, and nothing changes.
    """
    tested = await model_choice.choose(
        rt.db,
        rt.settings,
        base_url=body.base_url,
        model=body.model,
        writing_model=body.writing_model,
        num_ctx=body.num_ctx,
    )
    return s.ModelChosen(current=_in_use(tested.current), milliseconds=tested.milliseconds)


@api.delete("/system/model", tags=["system"])
async def reset_model(rt: Rt, _user: TheOwner) -> s.ModelInUse:
    """Back to the settings' model (.env)."""
    return _in_use(await model_choice.reset(rt.db, rt.settings))


# ─── accounts ────────────────────────────────────────────────────────────────


@api.post("/auth/sign-in", tags=["auth"])
async def sign_in(body: s.SignIn, request: Request, response: Response, rt: Rt) -> s.Me:
    result = await auth.sign_in(
        rt.db,
        rt.settings,
        body.email,
        body.password,
        request.headers.get("user-agent", ""),
        device=request.cookies.get(device_cookie_name(rt)),
    )
    if result.error == ErrorCode.SIGN_IN_LOCKED:
        wait = result.retry_after or 60
        raise TooManyRequests(
            ErrorCode.SIGN_IN_LOCKED,
            "Too many failed sign-ins; try again later",
            extra={"retry_after": wait},
            headers={"Retry-After": str(wait)},
        )
    if result.error == ErrorCode.ACCOUNT_DISABLED:
        raise PermissionDenied(ErrorCode.ACCOUNT_DISABLED, "This account is turned off; ask the owner of this apply")
    if result.error is not None or result.user is None or result.token is None:
        raise Unauthenticated(ErrorCode.SIGN_IN_FAILED, "The email or password is not right")
    return _signed_in(rt, response, result)


async def _setup(rt) -> s.Setup:
    if not rt.settings.web_setup:
        return s.Setup(open=False, first_run=False, mail=rt.settings.mail_enabled)
    async with rt.db.transaction() as session:
        first = not await users_repo.owner_exists(session)
        return s.Setup(
            open=first or await auth.registration_open(session), first_run=first, mail=rt.settings.mail_enabled
        )


@api.get("/auth/setup", tags=["auth"])
async def setup(rt: Rt) -> s.Setup:
    """
    Whether "Create an account" is offered: on the first run (the owner's), then while the owner keeps
    registration open. Never with web setup off (accounts are made with `apply init`).
    """
    return await _setup(rt)


# Requests from one address an hour, in this process's memory: enough to stop a script filling the database with
# accounts or someone's inbox with links.
REGISTRATIONS_PER_HOUR = 5
FORGOTTEN_PER_HOUR = 5


def _count(request: Request, what: str, per_hour: int, detail: str) -> None:
    if not hasattr(request.app.state, what):
        setattr(request.app.state, what, {})
    made: dict[str, list[float]] = getattr(request.app.state, what)
    now = time.monotonic()
    address = request.client.host if request.client else "?"
    recent = [t for t in made.get(address, []) if now - t < 3600]
    if len(recent) >= per_hour:
        raise TooManyRequests(ErrorCode.TOO_MANY_REQUESTS, detail, headers={"Retry-After": "3600"})
    if len(made) > 10_000:
        made.clear()
    made[address] = [*recent, now]


@api.post("/auth/register", tags=["auth"], status_code=status.HTTP_201_CREATED)
async def register(body: s.Register, request: Request, response: Response, rt: Rt) -> s.Me:
    """
    Make an account and sign in: the owner's on the first run, anyone's after that while registration is open
    (403 REGISTRATION_CLOSED otherwise; 409 EMAIL_TAKEN). Web setup off: `apply init` only.
    """
    if not rt.settings.web_setup:
        raise Conflict(ErrorCode.OWNER_EXISTS, "Make the account with: apply init")
    _count(request, "registrations", REGISTRATIONS_PER_HOUR, "Too many new accounts from here; try later")
    user = await auth.create_account(rt.db, body.email, body.password, locale=body.locale)
    if body.demo:
        await demo.add_to(rt.db, user.id)
    result = await auth.sign_in(rt.db, rt.settings, body.email, body.password, request.headers.get("user-agent", ""))
    assert result.user is not None and result.token is not None
    return _signed_in(rt, response, result)


async def _send_reset(rt: Runtime, email: str) -> None:
    """After the answer: a link only if there's such an account, so how long the answer took says nothing."""
    try:
        link = await auth.request_reset(rt.db, rt.settings, email)
        if link is None:
            return
        await mail.send(
            rt.settings,
            mail.Mail(
                to=link.email,
                subject=mail_text("reset.subject", link.locale),
                text=mail_text(
                    "reset.body", link.locale, email=link.email, url=link.url, minutes=rt.settings.reset_minutes
                ),
            ),
        )
    except Exception:  # the person was already told "if there's an account"; the log says what failed
        logger.exception("Couldn't send a password reset email")


@api.post("/auth/forgot-password", tags=["auth"], status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: s.ForgotPassword, request: Request, background: BackgroundTasks, rt: Rt) -> None:
    """
    Email a link to choose a new password, if there's an account with this email. The answer is the same
    whether or not there is (202), and the email is sent after it. 409 MAIL_NOT_SET_UP with no SMTP server.
    """
    if not rt.settings.mail_enabled:
        raise Conflict(ErrorCode.MAIL_NOT_SET_UP, "This apply can't send email; ask its owner")
    _count(request, "forgotten", FORGOTTEN_PER_HOUR, "Too many reset requests from here; try later")
    background.add_task(_send_reset, rt, body.email)


@api.post("/auth/reset-password/check", tags=["auth"])
async def check_reset(body: s.ResetToken, rt: Rt) -> s.ResetFor:
    """The account a reset link is for, while it works (404 RESET_LINK_INVALID once used or expired)."""
    async with rt.db.transaction() as session:
        return s.ResetFor(email=await auth.reset_email(session, body.token))


@api.post("/auth/reset-password", tags=["auth"], status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: s.ResetPassword, rt: Rt) -> None:
    """
    A new password from a reset link. Every session of the account ends, so the person signs in again; the
    link and any other of the account's stop working.
    """
    await auth.reset_password(rt.db, body.token, body.password)


def _signed_in(rt, response: Response, result) -> s.Me:
    """The session cookie, and the known-device one for a browser that's new to this account."""
    response.set_cookie(
        cookie_name(rt),
        result.token,
        max_age=rt.settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=rt.settings.secure_cookies,
        path="/",
    )
    if result.device:  # this browser is known from now on: a lock someone else causes won't shut it out
        response.set_cookie(
            device_cookie_name(rt),
            result.device,
            max_age=400 * 86400,  # the most browsers keep a cookie
            httponly=True,
            samesite="strict",
            secure=rt.settings.secure_cookies,
            path="/",
        )
    return s.Me.model_validate(result.user)


@api.get("/system/registration", tags=["people"])
async def get_registration(rt: Rt, _user: TheOwner) -> s.Registration:
    async with rt.db.transaction() as session:
        return s.Registration(open=await auth.registration_open(session))


@api.put("/system/registration", tags=["people"])
async def set_registration(body: s.Registration, rt: Rt, _user: TheOwner) -> s.Registration:
    """Open or close "Create an account" on the sign-in page. Existing accounts are untouched."""
    async with rt.db.transaction() as session:
        return s.Registration(open=await auth.set_registration(session, body.open))


@api.get("/people", tags=["people"])
async def list_people(rt: Rt, _user: TheOwner) -> s.People:
    """Every account on this apply (never what's in them)."""
    async with rt.db.transaction() as session:
        return s.People(items=[s.PersonOut.model_validate(p) for p in await people.list_(session)])


@api.post("/people/{person_id}/disable", tags=["people"])
async def disable_person(person_id: str, rt: Rt, _user: TheOwner) -> s.PersonOut:
    async with rt.db.transaction() as session:
        return s.PersonOut.model_validate(await people.set_disabled(session, person_id, True))


@api.post("/people/{person_id}/enable", tags=["people"])
async def enable_person(person_id: str, rt: Rt, _user: TheOwner) -> s.PersonOut:
    async with rt.db.transaction() as session:
        return s.PersonOut.model_validate(await people.set_disabled(session, person_id, False))


@api.delete("/people/{person_id}", tags=["people"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(person_id: str, rt: Rt, _user: TheOwner) -> None:
    """The account and everything in it, its files in the bucket too. The owner's own can't be deleted."""
    async with rt.db.transaction() as session:
        gone = await people.delete(session, person_id)
    await rt.files.delete_prefix(f"owners/{gone}/")


@api.post("/auth/sign-out", tags=["auth"], status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(request: Request, response: Response, rt: Rt) -> None:
    token = request.cookies.get(cookie_name(rt))
    if token:
        await auth.sign_out(rt.db, token)
    response.delete_cookie(cookie_name(rt), path="/", secure=rt.settings.secure_cookies, httponly=True, samesite="lax")


@api.get("/auth/me", tags=["auth"])
async def me(user: Owner) -> s.Me:
    return s.Me.model_validate(user)


@api.patch("/auth/me", tags=["auth"])
async def update_me(body: s.MeChanges, rt: Rt, user: Owner) -> s.Me:
    """The account's language (the web app also keeps it in a cookie, for before sign-in)."""
    async with rt.db.transaction() as session:
        return s.Me.model_validate(await auth.update_account(session, user.id, body.model_dump(exclude_unset=True)))


# ─── packs ───────────────────────────────────────────────────────────────────


async def _pack_out(rt: Runtime, key: str, owner_id: str) -> s.PackOut:
    pack = all_packs()[key]
    async with rt.db.transaction() as session:
        pipeline = await packs_repo.default_pipeline(session, key, owner_id)
        if pipeline is None:
            raise NotFound(ErrorCode.PACK_NOT_FOUND, f"The {key} pack has no pipeline yet (start-up syncs it)")
        stages = await packs_repo.stages_of(session, pipeline.id)
    row = pack.registry_row()
    return s.PackOut(
        key=pack.key,
        version=pack.version,
        label=s.Label(**pack.label),
        description=s.Label(**pack.description),
        profile_kinds=list(pack.profile_kinds),
        search_options=sorted(pack.search_options),
        auto=pack.auto,
        profile_schema=row["profile_schema"],
        opportunity_schema=row["opportunity_schema"],
        document_types=row["document_types"],
        pipeline=s.PipelineOut(
            id=pipeline.id,
            key=pipeline.key,
            label=s.Label(**pipeline.label),
            stages=[s.StageOut.model_validate(st) for st in stages],
        ),
        category_labels={k: s.Label(**v) for k, v in CATEGORY_LABELS.items()},
        action_labels={k: s.Label(**v) for k, v in ACTION_LABELS.items()},
        profile_kind_labels={k: s.Label(**v) for k, v in PROFILE_KIND_LABELS.items()},
    )


@api.get("/packs", tags=["packs"])
async def list_packs(rt: Rt, user: Owner) -> s.Packs:
    return s.Packs(items=[await _pack_out(rt, key, user.id) for key in sorted(all_packs())])


@api.get("/packs/{key}", tags=["packs"])
async def get_pack(key: str, rt: Rt, user: Reader) -> s.PackOut:
    find_pack(key)
    return await _pack_out(rt, key, user.id)


# ─── profiles ────────────────────────────────────────────────────────────────


@api.get("/profiles", tags=["profiles"])
async def list_profiles(
    rt: Rt, user: Owner, pack: str | None = None, after: After = None, limit: Limit = 50
) -> s.Profiles:
    async with rt.db.transaction() as session:
        rows, cursor = await profiles.list_(session, user.id, pack=pack, after=after, limit=limit)
        return s.Profiles(items=[s.ProfileOut.model_validate(r) for r in rows], next_cursor=cursor)


@api.post("/profiles", tags=["profiles"], status_code=status.HTTP_201_CREATED)
async def create_profile(body: s.NewProfile, rt: Rt, user: Owner) -> s.ProfileOut:
    async with rt.db.transaction() as session:
        row = await profiles.create(session, user.id, **body.model_dump())
        return s.ProfileOut.model_validate(row)


@api.get("/profiles/{profile_id}", tags=["profiles"])
async def get_profile(profile_id: str, rt: Rt, user: Owner) -> s.ProfileOut:
    async with rt.db.transaction() as session:
        return s.ProfileOut.model_validate(await profiles.get(session, user.id, profile_id))


@api.patch("/profiles/{profile_id}", tags=["profiles"])
async def update_profile(profile_id: str, body: s.ProfileChanges, rt: Rt, user: Owner) -> s.ProfileOut:
    async with rt.db.transaction() as session:
        row = await profiles.update(session, user.id, profile_id, body.model_dump(exclude_unset=True))
        return s.ProfileOut.model_validate(row)


@api.delete("/profiles/{profile_id}", tags=["profiles"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: str, rt: Rt, user: Owner) -> None:
    async with rt.db.transaction() as session:
        source_key = await profiles.delete(session, user.id, profile_id)
    if source_key:
        await files.delete(rt, source_key)


@api.post("/profiles/import", tags=["profiles"], status_code=status.HTTP_202_ACCEPTED)
async def import_profile(
    rt: Rt,
    user: Owner,
    file: Annotated[UploadFile, File(description="A resume (or the pack's document): PDF, .docx or text")],
    pack: Annotated[str, Form(pattern=r"^[a-z][a-z0-9_]{0,39}$")] = DEFAULT_PACK,
    name: Annotated[str | None, Form(max_length=200)] = None,
    is_default: Annotated[bool | None, Form()] = None,
) -> s.ProfileOut:
    """
    A profile made from a document. 202 with the profile, saved at once; the model reads the document into its
    fields in the background (``reading.status`` pending → ready, or failed with a code). Poll it, then check
    every field. 422 UPLOAD_TOO_LARGE, UPLOAD_UNSUPPORTED, or UPLOAD_NO_TEXT (a scan with no text in it).
    """
    data = await file.read(rt.settings.upload_max_bytes + 1)
    row = await profiles.import_document(
        rt, user.id, pack=pack, data=data, filename=file.filename or "", name=name, is_default=is_default
    )
    return s.ProfileOut.model_validate(row)


@api.post("/profiles/{profile_id}/duplicate", tags=["profiles"], status_code=status.HTTP_201_CREATED)
async def duplicate_profile(
    profile_id: str, rt: Rt, user: Owner, body: s.DuplicateProfile | None = None
) -> s.ProfileOut:
    """A copy of the profile to change what's different ("Name (copy)" unless named), never the default."""
    async with rt.db.transaction() as session:
        row = await profiles.duplicate(session, user.id, profile_id, name=body.name if body else None)
        return s.ProfileOut.model_validate(row)


@api.post("/profiles/{profile_id}/read", tags=["profiles"], status_code=status.HTTP_202_ACCEPTED)
async def read_profile_again(profile_id: str, rt: Rt, user: Owner) -> s.ProfileOut:
    """Read the profile's document again; what's read replaces its fields. 409 PROFILE_NOT_READ without one."""
    async with rt.db.transaction() as session:
        return s.ProfileOut.model_validate(await profiles.read_again(session, user.id, profile_id))


@api.get(
    "/profiles/{profile_id}/source",
    tags=["profiles"],
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}, "description": "The document, as uploaded"}},
)
async def profile_source(profile_id: str, rt: Rt, user: Owner) -> Response:
    """The document the profile was made from. 409 PROFILE_NOT_READ without one."""
    async with rt.db.transaction() as session:
        found, data = await profiles.source(rt, session, user.id, profile_id)
    filename = quote(found.get("name") or "document")
    return Response(
        data,
        media_type=CONTENT_TYPES.get(found.get("kind"), "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ─── opportunities ───────────────────────────────────────────────────────────


@api.get("/opportunities", tags=["opportunities"])
async def list_opportunities(
    rt: Rt, user: Owner, pack: str | None = None, after: After = None, limit: Limit = 50
) -> s.Opportunities:
    async with rt.db.transaction() as session:
        rows, cursor = await opportunities.list_(session, user.id, pack=pack, after=after, limit=limit)
        return s.Opportunities(items=[s.OpportunityOut.model_validate(r) for r in rows], next_cursor=cursor)


@api.post(
    "/opportunities",
    tags=["opportunities"],
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": s.OpportunityOut, "description": "Pasted before: the same opportunity"}},
)
async def paste_opportunity(body: s.Paste, response: Response, rt: Rt, user: Writer) -> s.OpportunityOut:
    """Paste a link or the text. New: 201; the same link or text again: 200 with the existing one."""
    row, created = await opportunities.paste(
        rt, user.id, pack_key=body.pack, url=body.url, text=body.text, html=body.html
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return s.OpportunityOut.model_validate(row)


@api.get("/opportunities/{opportunity_id}", tags=["opportunities"])
async def get_opportunity(opportunity_id: str, rt: Rt, user: Reader) -> s.OpportunityOut:
    async with rt.db.transaction() as session:
        return s.OpportunityOut.model_validate(await opportunities.get(session, user.id, opportunity_id))


@api.patch("/opportunities/{opportunity_id}", tags=["opportunities"])
async def update_opportunity(opportunity_id: str, body: s.OpportunityChanges, rt: Rt, user: Owner) -> s.OpportunityOut:
    async with rt.db.transaction() as session:
        row = await opportunities.update(session, user.id, opportunity_id, body.model_dump(exclude_unset=True))
        return s.OpportunityOut.model_validate(row)


@api.post("/opportunities/{opportunity_id}/extract", tags=["opportunities"], status_code=status.HTTP_202_ACCEPTED)
async def extract_opportunity(opportunity_id: str, rt: Rt, user: Owner) -> s.OpportunityOut:
    """Have the model read the opportunity's text again."""
    return s.OpportunityOut.model_validate(await opportunities.extract_again(rt, user.id, opportunity_id))


# ─── applications ────────────────────────────────────────────────────────────


@api.get("/applications", tags=["applications"])
async def list_applications(
    rt: Rt, user: Owner, pack: str | None = None, stage: str | None = None, after: After = None, limit: Limit = 50
) -> s.Applications:
    async with rt.db.transaction() as session:
        rows, cursor = await applications.list_(session, user.id, pack=pack, stage_code=stage, after=after, limit=limit)
        return s.Applications(items=[s.ApplicationOut.model_validate(r) for r in rows], next_cursor=cursor)


@api.post("/applications", tags=["applications"], status_code=status.HTTP_201_CREATED)
async def create_application(body: s.NewApplication, rt: Rt, user: Writer) -> s.ApplicationOut:
    async with rt.db.transaction() as session:
        row = await applications.create(
            session, user.id, opportunity_id=body.opportunity_id, profile_id=body.profile_id, notes=body.notes
        )
        return s.ApplicationOut.model_validate(row)


@api.get("/applications/by-url", tags=["applications"])
async def application_by_url(
    rt: Rt, user: Reader, url: Annotated[list[str], Query(min_length=1, max_length=8)]
) -> s.Lookup:
    """The opportunity (and application, if there is one) for a page: the form the extension is looking at."""
    async with rt.db.transaction() as session:
        opp, application = await fill.lookup(session, user.id, url)
        return s.Lookup(
            opportunity=s.OpportunityOut.model_validate(opp),
            application=s.ApplicationOut.model_validate(application) if application else None,
        )


@api.get("/applications/{application_id}", tags=["applications"])
async def get_application(application_id: str, rt: Rt, user: Reader) -> s.ApplicationOut:
    async with rt.db.transaction() as session:
        return s.ApplicationOut.model_validate(await applications.get(session, user.id, application_id))


@api.patch("/applications/{application_id}", tags=["applications"])
async def update_application(application_id: str, body: s.ApplicationChanges, rt: Rt, user: Owner) -> s.ApplicationOut:
    async with rt.db.transaction() as session:
        row = await applications.update(session, user.id, application_id, body.model_dump(exclude_unset=True))
        return s.ApplicationOut.model_validate(row)


@api.delete("/applications/{application_id}", tags=["applications"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(application_id: str, rt: Rt, user: Owner) -> None:
    """The application and everything made for it; its posting stays. 409 while Auto is sending it."""
    async with rt.db.transaction() as session:
        await applications.delete(session, user.id, application_id)


@api.post("/applications/{application_id}/stage", tags=["applications"])
async def move_application(application_id: str, body: s.Move, rt: Rt, user: Owner) -> s.ApplicationOut:
    async with rt.db.transaction() as session:
        row = await applications.move(session, user.id, application_id, stage_code=body.stage_code, note=body.note)
        return s.ApplicationOut.model_validate(row)


@api.get("/applications/{application_id}/history", tags=["applications"])
async def application_history(application_id: str, rt: Rt, user: Owner) -> s.History:
    async with rt.db.transaction() as session:
        rows = await applications.history(session, user.id, application_id)
        return s.History(items=[s.HistoryEntry.model_validate(r) for r in rows])


# ─── documents ───────────────────────────────────────────────────────────────


@api.post(
    "/applications/{application_id}/documents",
    tags=["documents"],
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"model": s.DocumentOut, "description": "One is already being written: that one"}},
)
async def request_document(
    application_id: str, body: s.DocumentRequest, response: Response, rt: Rt, user: Owner
) -> s.DocumentOut:
    """Write a document in the background. 202 with the pending document; poll it until it is ready or failed."""
    async with rt.db.transaction() as session:
        row, queued = await documents.request(
            session, user.id, application_id, document_type=body.document_type, profile_id=body.profile_id
        )
        if not queued:
            response.status_code = status.HTTP_200_OK
        return s.DocumentOut.model_validate(row)


@api.get("/applications/{application_id}/documents", tags=["documents"])
async def list_documents(application_id: str, rt: Rt, user: Owner) -> s.Documents:
    async with rt.db.transaction() as session:
        rows = await documents.list_(session, user.id, application_id)
        return s.Documents(items=[s.DocumentOut.model_validate(r) for r in rows])


@api.get("/applications/{application_id}/documents/{document_id}", tags=["documents"])
async def get_document(application_id: str, document_id: str, rt: Rt, user: Owner) -> s.DocumentOut:
    async with rt.db.transaction() as session:
        return s.DocumentOut.model_validate(await documents.get(session, user.id, application_id, document_id))


# ─── discovery (api/discovery.py) ──────────────────────────────────────

from .auto import automatic  # noqa: E402
from .discovery import discovery  # noqa: E402
from .extension import extension  # noqa: E402
from .review import reviewing  # noqa: E402

api.include_router(discovery)
api.include_router(reviewing)
api.include_router(extension)
api.include_router(automatic)
