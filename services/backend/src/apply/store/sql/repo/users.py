"""Accounts and sessions."""

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KnownDevice, PasswordReset, Session, User


async def owner_exists(session: AsyncSession) -> bool:
    return (await session.execute(select(func.count()).select_from(User).where(User.is_owner))).scalar_one() > 0


async def lock_owner_creation(session: AsyncSession) -> None:
    """Serialise `apply init` runs, so two at once can't both create an owner."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('apply.owner'))"))


async def by_email(session: AsyncSession, email: str, *, for_update: bool = False) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def known_device(session: AsyncSession, owner_id: str, token_hash: str) -> bool:
    row = (
        await session.execute(
            select(KnownDevice).where(KnownDevice.owner_id == owner_id, KnownDevice.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if row is not None:
        row.last_seen_at = datetime.now(UTC)
    return row is not None


async def add_known_device(session: AsyncSession, *, owner_id: str, token_hash: str) -> None:
    session.add(KnownDevice(owner_id=owner_id, token_hash=token_hash))
    await session.flush()


async def add_session(
    session: AsyncSession, *, owner_id: str, token_hash: str, expires_at: datetime, user_agent: str
) -> Session:
    row = Session(owner_id=owner_id, token_hash=token_hash, expires_at=expires_at, user_agent=user_agent[:300])
    session.add(row)
    await session.flush()
    return row


async def session_by_token_hash(session: AsyncSession, token_hash: str) -> tuple[Session, User] | None:
    row = (
        await session.execute(
            select(Session, User).join(User, User.id == Session.owner_id).where(Session.token_hash == token_hash)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def touch_session(session: AsyncSession, session_id: str, *, expires_at: datetime) -> None:
    await session.execute(
        update(Session).where(Session.id == session_id).values(last_seen_at=func.now(), expires_at=expires_at)
    )


async def delete_session(session: AsyncSession, token_hash: str) -> None:
    await session.execute(delete(Session).where(Session.token_hash == token_hash))


async def delete_expired_sessions(session: AsyncSession) -> int:
    result = await session.execute(delete(Session).where(Session.expires_at < func.now()))
    return result.rowcount or 0


async def end_sessions(session: AsyncSession, owner_id: str) -> None:
    """Signed out everywhere."""
    await session.execute(delete(Session).where(Session.owner_id == owner_id))


async def add_reset(session: AsyncSession, *, owner_id: str, token_hash: str, expires_at: datetime) -> None:
    session.add(PasswordReset(owner_id=owner_id, token_hash=token_hash, expires_at=expires_at))
    await session.flush()


async def resets_since(session: AsyncSession, owner_id: str, since: datetime) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(PasswordReset)
            .where(PasswordReset.owner_id == owner_id, PasswordReset.created_at >= since)
        )
    ).scalar_one()


async def reset_by_token_hash(session: AsyncSession, token_hash: str) -> tuple[PasswordReset, User] | None:
    row = (
        await session.execute(
            select(PasswordReset, User)
            .join(User, User.id == PasswordReset.owner_id)
            .where(PasswordReset.token_hash == token_hash)
            .with_for_update(of=PasswordReset)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def use_up_resets(session: AsyncSession, owner_id: str, now: datetime) -> None:
    await session.execute(
        update(PasswordReset)
        .where(PasswordReset.owner_id == owner_id, PasswordReset.used_at.is_(None))
        .values(used_at=now)
    )


async def delete_old_resets(session: AsyncSession, before: datetime) -> int:
    result = await session.execute(delete(PasswordReset).where(PasswordReset.expires_at < before))
    return result.rowcount or 0
