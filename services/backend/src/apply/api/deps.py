"""
What every handler needs: the runtime, the signed-in owner, and the same-origin check on unsafe requests.

Two ways to be the owner:

- a **session** (the web app's cookie): every route;
- a **personal API token** (``Authorization: Bearer apl_…``, the extension): only routes that ask for one of its
  scopes with ``allow_token``. A request carrying a token is judged by the token alone; any cookie is ignored.
"""

from typing import Annotated

from fastapi import Depends, Request

from apply.errors import ErrorCode, PermissionDenied, Unauthenticated
from apply.logic import auth, tokens
from apply.runtime import Runtime
from apply.store.sql.models import ApiToken, User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def device_cookie_name(rt: Runtime) -> str:
    return "__Host-apply_device" if rt.settings.secure_cookies else "apply_device"


def cookie_name(rt: Runtime) -> str:
    # __Host-: the browser only keeps it from a secure origin, for this host and path "/", never a parent domain.
    return "__Host-apply_session" if rt.settings.secure_cookies else "apply_session"


def runtime(request: Request) -> Runtime:
    return request.app.state.runtime


Rt = Annotated[Runtime, Depends(runtime)]


async def same_origin(request: Request, rt: Rt) -> None:
    """
    CSRF: on top of SameSite=Lax, an unsafe request from a browser must come from the web app or the API itself.
    Browsers always send Origin (or Sec-Fetch-Site) on a cross-site POST; a request with neither isn't from one.
    """
    if request.method in SAFE_METHODS or bearer(request) is not None:
        return  # a token isn't sent by the browser on its own, so another site can't make use of it
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in rt.settings.own_origins:
        raise PermissionDenied(ErrorCode.ORIGIN_NOT_ALLOWED, f"Requests from {origin} are not accepted")
    if origin is None and request.headers.get("sec-fetch-site") == "cross-site":
        raise PermissionDenied(ErrorCode.ORIGIN_NOT_ALLOWED, "Cross-site requests are not accepted")


def bearer(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    return (value.strip() or None) if scheme.lower() == "bearer" else None


def token_of(request: Request) -> ApiToken | None:
    """The token a request was made with (None for a session)."""
    return getattr(request.state, "token", None)


async def current_user(request: Request, rt: Rt) -> User:
    if bearer(request) is not None:
        raise PermissionDenied(ErrorCode.TOKEN_NOT_ALLOWED, "This needs a signed-in session, not a token")
    token = request.cookies.get(cookie_name(rt))
    if not token:
        raise Unauthenticated(ErrorCode.UNAUTHENTICATED, "Sign in first")
    async with rt.db.transaction() as session:
        user = await auth.authenticate(session, rt.settings, token)
    if user is None:
        raise Unauthenticated(ErrorCode.UNAUTHENTICATED, "The session has ended; sign in again")
    return user


def allow_token(scope: str | None):
    """The owner, from a session or from a token with ``scope`` (None: any token)."""

    async def owner(request: Request, rt: Rt) -> User:
        secret = bearer(request)
        if secret is None:
            return await current_user(request, rt)
        async with rt.db.transaction() as session:
            found = await tokens.authenticate(session, secret)
        if found is None:
            raise Unauthenticated(ErrorCode.TOKEN_INVALID, "That token is unknown, revoked or expired")
        token, user = found
        if scope is not None and scope not in token.scopes:
            raise PermissionDenied(ErrorCode.TOKEN_SCOPE_MISSING, f"The token needs {scope}", extra={"scope": scope})
        request.state.token = token
        return user

    return owner


Reader = Annotated[User, Depends(allow_token("applications:read"))]
Writer = Annotated[User, Depends(allow_token("applications:write"))]
Submitter = Annotated[User, Depends(allow_token("submissions:write"))]
ProfileReader = Annotated[User, Depends(allow_token("profiles:read"))]
AnyToken = Annotated[User, Depends(allow_token(None))]


async def the_owner(user: Annotated[User, Depends(current_user)]) -> User:
    """The owner of this apply, signed in: for what's the install's, not a person's (the model, accounts)."""
    if not user.is_owner:
        raise PermissionDenied(ErrorCode.OWNER_ONLY, "Only the owner of this apply can change this")
    return user


TheOwner = Annotated[User, Depends(the_owner)]
