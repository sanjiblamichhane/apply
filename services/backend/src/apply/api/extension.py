"""Personal API tokens, and what the browser extension reads to fill a form (routes under /api/v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from apply.logic import copy, fill, tokens
from apply.store.sql.models import User

from . import schemas as s
from .deps import AnyToken, ProfileReader, Reader, Rt, current_user, token_of

Owner = Annotated[User, Depends(current_user)]
extension = APIRouter()


@extension.get("/tokens", tags=["tokens"])
async def list_tokens(rt: Rt, user: Owner) -> s.Tokens:
    async with rt.db.transaction() as session:
        return s.Tokens(items=[s.TokenOut.model_validate(t) for t in await tokens.list_(session, user.id)])


@extension.post("/tokens", tags=["tokens"], status_code=status.HTTP_201_CREATED)
async def create_token(body: s.NewToken, rt: Rt, user: Owner) -> s.CreatedToken:
    """A token for the extension. Its secret is in this answer only: apply keeps a hash."""
    async with rt.db.transaction() as session:
        made = await tokens.create(
            session,
            user.id,
            name=body.name,
            kind=body.kind,
            scopes=list(body.scopes),
            expires_in_days=body.expires_in_days,
        )
        return s.CreatedToken(token=s.TokenOut.model_validate(made.token), secret=made.secret)


@extension.delete("/tokens/{token_id}", tags=["tokens"])
async def revoke_token(token_id: str, rt: Rt, user: Owner) -> s.TokenOut:
    """Stops working at once. A revoked token stays listed, so you can see what it was."""
    async with rt.db.transaction() as session:
        return s.TokenOut.model_validate(await tokens.revoke(session, user.id, token_id))


@extension.get("/tokens/current", tags=["tokens"])
async def current_token(request: Request, user: AnyToken) -> s.Caller:
    """Who this is: the extension checks its token here, and speaks the owner's language."""
    token = token_of(request)
    return s.Caller(email=user.email, locale=user.locale, token=s.TokenOut.model_validate(token) if token else None)


@extension.get("/applications/{application_id}/fill", tags=["applications"])
async def fill_sheet(application_id: str, rt: Rt, user: Reader) -> s.FillSheet:
    """What goes into the application's form: profile values, saved answers, documents (with their PDFs)."""
    async with rt.db.transaction() as session:
        found = await fill.sheet(session, user.id, application_id)
        return s.FillSheet(
            application=s.ApplicationOut.model_validate(found["application"]),
            opportunity=s.OpportunityOut.model_validate(found["opportunity"]),
            values=found["values"],
            answers=[s.AnswerOut.model_validate(a) for a in found["answers"]],
            documents=[s.FillDocument(**d) for d in found["documents"]],
        )


def _copy_profile(p) -> s.CopyProfile:
    return s.CopyProfile(id=p.id, pack=p.pack, name=p.name, is_default=p.is_default)


@extension.get("/copy-sheet", tags=["extension"])
async def copy_sheet(
    rt: Rt, user: ProfileReader, profile_id: str | None = None, pack: str | None = None
) -> s.CopySheetOut:
    """
    A profile's values for the extension's copy panel (the pack's default profile unless one is chosen), each
    ready to paste, and the saved answers. Needs a token with profiles:read, or a session.
    """
    async with rt.db.transaction() as session:
        found = await copy.sheet(session, user.id, profile_id, pack)
    return s.CopySheetOut(
        profile=_copy_profile(found.profile) if found.profile else None,
        profiles=[_copy_profile(p) for p in found.profiles],
        tabs=[
            s.CopyTabOut(
                key=t.key,
                label=dict(t.label),
                groups=[
                    s.CopyGroupOut(
                        title=g.title,
                        items=[
                            s.CopyItemOut(label=dict(i.label), value=i.value, sensitive=i.sensitive) for i in g.items
                        ],
                    )
                    for g in t.groups
                ],
            )
            for t in found.tabs
        ],
    )
