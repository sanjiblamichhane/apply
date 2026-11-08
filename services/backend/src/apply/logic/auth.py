"""
The owner account and its sessions.

- Passwords: argon2id (hashed off the event loop), at least 12 characters.
- Sessions: a 32-byte random token in an httpOnly cookie; only its SHA-256 is stored, so a copy of the database
  signs no one in. Sliding expiry, renewed at most hourly.
- Sign-in: the same answer and about the same time whether or not the email exists; repeated failures lock the
  account for a while.
"""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, InvalidArgument, NotFound, PermissionDenied
from apply.i18n import is_locale
from apply.settings import AppSettings
from apply.store.sql import Database
from apply.store.sql.models import InstallSettings, PasswordReset, User
from apply.store.sql.repo import users

MIN_PASSWORD = 12
_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("not a real password, only for timing")


def _now() -> datetime:
    return datetime.now(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    def check() -> bool:
        try:
            return _hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    return await asyncio.to_thread(check)


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise InvalidArgument(ErrorCode.PASSWORD_TOO_SHORT, f"A password needs at least {MIN_PASSWORD} characters")


async def create_owner(db: Database, email: str, password: str, *, locale: str = "en") -> User:
    """`apply init`: the one owner account. Refuses if there is one already."""
    email = email.strip().lower()
    if "@" not in email or len(email) > 320:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "That is not an email address")
    check_password(password)
    password_hash = await hash_password(password)
    async with db.transaction() as session:
        await users.lock_owner_creation(session)
        if await users.owner_exists(session):
            raise Conflict(ErrorCode.OWNER_EXISTS, "apply already has an owner")
        user = User(
            email=email, password_hash=password_hash, is_owner=True, locale=locale if is_locale(locale) else "en"
        )
        session.add(user)
        await session.flush()
        return user


async def registration_open(session: AsyncSession) -> bool:
    """Whether anyone may create an account now (the owner's switch; open until they close it)."""
    row = await session.get(InstallSettings, "current")
    return row.registration_open if row else True


async def set_registration(session: AsyncSession, open_: bool) -> bool:
    row = await session.get(InstallSettings, "current")
    if row is None:
        row = InstallSettings(id="current")
        session.add(row)
    row.registration_open = open_
    await session.flush()
    return open_


async def create_account(db: Database, email: str, password: str, *, locale: str = "en") -> User:
    """
    Someone's own account, from the sign-in page: the owner's on the first run, anyone's after that while the
    owner keeps registration open (REGISTRATION_CLOSED otherwise). Each account sees only its own data.
    """
    email = email.strip().lower()
    if "@" not in email or len(email) > 320:
        raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "That is not an email address")
    check_password(password)
    password_hash = await hash_password(password)
    async with db.transaction() as session:
        await users.lock_owner_creation(session)
        first = not await users.owner_exists(session)
        if not first and not await registration_open(session):
            raise PermissionDenied(ErrorCode.REGISTRATION_CLOSED, "New accounts are closed on this apply")
        if await users.by_email(session, email) is not None:
            raise Conflict(ErrorCode.EMAIL_TAKEN, "There's an account with that email already: sign in")
        user = User(
            email=email, password_hash=password_hash, is_owner=first, locale=locale if is_locale(locale) else "en"
        )
        session.add(user)
        await session.flush()
        return user


@dataclass(frozen=True)
class SignIn:
    user: User | None = None
    token: str | None = None
    error: ErrorCode | None = None
    retry_after: int | None = None  # seconds, when locked
    device: str | None = None  # a new known-device cookie to set (this browser wasn't known yet)


# Failed sign-ins for emails with no account, counted as for real ones, so a lock doesn't say which exist.
# In memory and bounded: it only has to look the same, not survive a restart.
_strangers: dict[str, tuple[int, datetime | None]] = {}
_STRANGERS_MAX = 10_000


def _stranger_failed(settings: AppSettings, email: str, now: datetime) -> SignIn:
    key = email.strip().lower()
    count, until = _strangers.get(key, (0, None))
    if until and until > now:
        return SignIn(error=ErrorCode.SIGN_IN_LOCKED, retry_after=max(1, int((until - now).total_seconds())))
    count += 1
    if len(_strangers) >= _STRANGERS_MAX:
        _strangers.clear()
    if count >= settings.sign_in_max_failures:
        _strangers[key] = (0, now + timedelta(minutes=settings.sign_in_lock_minutes))
        return SignIn(error=ErrorCode.SIGN_IN_LOCKED, retry_after=settings.sign_in_lock_minutes * 60)
    _strangers[key] = (count, None)
    return SignIn(error=ErrorCode.SIGN_IN_FAILED)


async def sign_in(
    db: Database, settings: AppSettings, email: str, password: str, user_agent: str, device: str | None = None
) -> SignIn:
    """
    Check a password and open a session. Failures are counted (and committed) before the caller answers, so
    the outcome is returned rather than raised.

    Repeated failures lock the account for a while, except from a browser it has signed in from before
    (``device``, the known-device cookie): someone guessing can't lock the owner out of their own browser.
    """
    async with db.transaction() as session:
        user = await users.by_email(session, email, for_update=True)
        now = _now()
        if user is None:
            await verify_password(_DUMMY_HASH, password)  # the same time as a real check
            return _stranger_failed(settings, email, now)
        known = device is not None and await users.known_device(session, user.id, hash_token(device))
        if user.locked_until and user.locked_until > now and not known:
            await verify_password(_DUMMY_HASH, password)  # locked or not, the same time
            return SignIn(
                error=ErrorCode.SIGN_IN_LOCKED, retry_after=max(1, int((user.locked_until - now).total_seconds()))
            )
        if not await verify_password(user.password_hash, password):
            user.failed_sign_ins += 1
            if user.failed_sign_ins >= settings.sign_in_max_failures:
                user.failed_sign_ins = 0
                user.locked_until = now + timedelta(minutes=settings.sign_in_lock_minutes)
                return SignIn(error=ErrorCode.SIGN_IN_LOCKED, retry_after=settings.sign_in_lock_minutes * 60)
            return SignIn(error=ErrorCode.SIGN_IN_FAILED)

        if user.disabled_at is not None:  # said only to someone who knows the password
            return SignIn(error=ErrorCode.ACCOUNT_DISABLED)
        if _hasher.check_needs_rehash(user.password_hash):
            user.password_hash = await hash_password(password)
        user.failed_sign_ins = 0
        user.locked_until = None
        user.last_sign_in_at = now
        new_device = None
        if not known:
            new_device = secrets.token_urlsafe(32)
            await users.add_known_device(session, owner_id=user.id, token_hash=hash_token(new_device))
        token = secrets.token_urlsafe(32)
        await users.add_session(
            session,
            owner_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(days=settings.session_days),
            user_agent=user_agent,
        )
        return SignIn(user=user, token=token, device=new_device)


async def authenticate(session: AsyncSession, settings: AppSettings, token: str) -> User | None:
    """The user a session cookie stands for, or None. Renews the session's expiry at most once an hour."""
    found = await users.session_by_token_hash(session, hash_token(token))
    if found is None:
        return None
    row, user = found
    now = _now()
    if row.expires_at <= now or user.disabled_at is not None:
        await users.delete_session(session, row.token_hash)
        return None
    if now - row.last_seen_at > timedelta(hours=1):
        await users.touch_session(session, row.id, expires_at=now + timedelta(days=settings.session_days))
    return user


# ─── forgotten passwords ─────────────────────────────────────────────────────

# Emails one account may be sent an hour; more requests are answered the same and send nothing.
RESETS_PER_HOUR = 3


@dataclass(frozen=True)
class ResetLink:
    email: str
    locale: str
    url: str


async def request_reset(db: Database, settings: AppSettings, email: str) -> ResetLink | None:
    """
    A link for "Forgot your password?", or None: no such account, turned off, or sent enough this hour. The
    caller answers the same either way. Only the token's hash is stored; the link is the web app's own address
    (``public_url``) with the token.
    """
    email = email.strip().lower()
    async with db.transaction() as session:
        user = await users.by_email(session, email, for_update=True)
        if user is None or user.disabled_at is not None:
            return None
        now = _now()
        if await users.resets_since(session, user.id, now - timedelta(hours=1)) >= RESETS_PER_HOUR:
            return None
        token = secrets.token_urlsafe(32)
        await users.add_reset(
            session,
            owner_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(minutes=settings.reset_minutes),
        )
        return ResetLink(
            email=user.email,
            locale=user.locale,
            url=f"{settings.public_url.rstrip('/')}/reset-password?{urlencode({'token': token})}",
        )


async def reset_email(session: AsyncSession, token: str) -> str:
    """The email a reset link is for, while the link still works (RESET_LINK_INVALID otherwise)."""
    _, user = await _usable_reset(session, token)
    return user.email


async def _usable_reset(session: AsyncSession, token: str) -> tuple[PasswordReset, User]:
    found = await users.reset_by_token_hash(session, hash_token(token)) if token else None
    if found is None:
        raise NotFound(ErrorCode.RESET_LINK_INVALID, "This link has expired or has been used")
    row, user = found
    if row.used_at is not None or row.expires_at <= _now() or user.disabled_at is not None:
        raise NotFound(ErrorCode.RESET_LINK_INVALID, "This link has expired or has been used")
    return row, user


async def reset_password(db: Database, token: str, password: str) -> str:
    """
    A new password from a reset link: the link and every other of the account's is used up, every session of
    it ends, and a sign-in lock is lifted. Returns the account's email.
    """
    check_password(password)
    password_hash = await hash_password(password)
    async with db.transaction() as session:
        row, user = await _usable_reset(session, token)
        await _set_password(session, user, password_hash)
        row.used_at = _now()
        return user.email


async def set_password(db: Database, email: str, password: str) -> None:
    """`apply password`: a new password from the command line, when no email can be sent."""
    check_password(password)
    password_hash = await hash_password(password)
    async with db.transaction() as session:
        user = await users.by_email(session, email.strip().lower(), for_update=True)
        if user is None:
            raise NotFound(ErrorCode.NOT_FOUND, "There's no account with that email")
        await _set_password(session, user, password_hash)


async def _set_password(session: AsyncSession, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    user.failed_sign_ins = 0
    user.locked_until = None
    await users.end_sessions(session, user.id)
    await users.use_up_resets(session, user.id, _now())
    await session.flush()


async def update_account(session: AsyncSession, user_id: str, changes: dict) -> User:
    user = await users.by_id(session, user_id)
    assert user is not None
    if is_locale(changes.get("locale")):
        user.locale = changes["locale"]
    if changes.get("time_zone"):
        try:
            ZoneInfo(changes["time_zone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidArgument(ErrorCode.VALIDATION_FAILED, f"No time zone {changes['time_zone']!r}") from exc
        user.time_zone = changes["time_zone"]
    if changes.get("briefing_hour") is not None:
        user.briefing_hour = int(changes["briefing_hour"])
    await session.flush()
    return user


async def sign_out(db: Database, token: str) -> None:
    async with db.transaction() as session:
        await users.delete_session(session, hash_token(token))
