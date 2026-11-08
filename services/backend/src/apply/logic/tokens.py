"""
Personal API tokens: how the extension acts for its person without a password.

- The secret is ``apl_`` + 32 random bytes, shown once. Only its SHA-256 is stored, with its first characters
  (``prefix``) so a person can tell tokens apart.
- Each token carries scopes. A route accepts a token only if it asks for one of them (api/deps.allow_token);
  every other route is for a signed-in session only, so a token can't change the profile or make more tokens.
- Tokens expire (90 days unless chosen otherwise) and can be revoked at once. Use is stamped at most hourly.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import ErrorCode, InvalidArgument
from apply.store.sql.models import ApiToken, User
from apply.store.sql.repo import tokens as repo

from .auth import hash_token

PREFIX = "apl_"
SCOPES = ("applications:read", "applications:write", "submissions:write", "profiles:read")
KINDS = ("extension",)
# What each kind of token may carry.
ALLOWED = {"extension": {"applications:read", "applications:write", "submissions:write", "profiles:read"}}


@dataclass(frozen=True)
class Created:
    token: ApiToken
    secret: str  # shown once, never stored


def looks_like_token(value: str) -> bool:
    return value.startswith(PREFIX) and 20 <= len(value) <= 100


def clean_scopes(scopes: list[str]) -> list[str]:
    unknown = sorted(set(scopes) - set(SCOPES))
    if unknown or not scopes:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"Scopes must be some of {', '.join(SCOPES)}")
    return [s for s in SCOPES if s in scopes]  # in a fixed order, without repeats


async def create(
    session: AsyncSession,
    owner_id: str,
    *,
    name: str,
    scopes: list[str],
    expires_in_days: int | None = 90,
    kind: str = "extension",
) -> Created:
    if kind not in KINDS:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"A token is for one of {', '.join(KINDS)}")
    scopes = clean_scopes(scopes)
    if not set(scopes) <= ALLOWED[kind]:
        raise InvalidArgument(
            ErrorCode.VALIDATION_FAILED, f"A {kind} token may have {', '.join(sorted(ALLOWED[kind]))}"
        )
    secret = PREFIX + secrets.token_urlsafe(32)
    token = ApiToken(
        owner_id=owner_id,
        name=name.strip()[:100] or "Browser extension",
        kind=kind,
        prefix=secret[:12],
        token_hash=hash_token(secret),
        scopes=scopes,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days) if expires_in_days else None,
    )
    session.add(token)
    await session.flush()
    return Created(token=token, secret=secret)


async def list_(session: AsyncSession, owner_id: str) -> list[ApiToken]:
    return list(await repo.list_(session, owner_id))


async def revoke(session: AsyncSession, owner_id: str, token_id: str) -> ApiToken:
    token = await repo.get(session, owner_id, token_id)
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        await session.flush()
    return token


def usable(token: ApiToken, now: datetime) -> bool:
    return token.revoked_at is None and (token.expires_at is None or token.expires_at > now)


async def authenticate(session: AsyncSession, secret: str) -> tuple[ApiToken, User] | None:
    """The token and its owner for a secret, or None if it is unknown, revoked or expired."""
    if not looks_like_token(secret):
        return None
    found = await repo.by_hash(session, hash_token(secret))
    if found is None:
        return None
    token, user = found
    now = datetime.now(UTC)
    if not usable(token, now) or user.disabled_at is not None:
        return None
    if token.last_used_at is None or now - token.last_used_at > timedelta(hours=1):
        await repo.touch(session, token.id, now)
    return token, user
