"""
The accounts on this apply, as its owner manages them: who has one, turning one off (and on), and deleting
one with everything in it. The owner never sees what's in another account; the owner's own account can't be
turned off or deleted here.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete as delete_
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apply.errors import Conflict, ErrorCode, NotFound
from apply.store.sql.models import ApiToken, AutoRun, Session, User
from apply.store.sql.repo import auto as auto_repo


async def list_(session: AsyncSession) -> Sequence[User]:
    return (await session.execute(select(User).order_by(User.created_at, User.id))).scalars().all()


async def _other(session: AsyncSession, person_id: str) -> User:
    person = await session.get(User, person_id, with_for_update=True)
    if person is None:
        raise NotFound(ErrorCode.NOT_FOUND, "There's no such account")
    if person.is_owner:
        raise Conflict(ErrorCode.ACCOUNT_IS_OWNER, "The owner's account can't be changed here")
    return person


async def set_disabled(session: AsyncSession, person_id: str, disabled: bool) -> User:
    """
    Off: signed out everywhere, its tokens revoked, it can't sign in, its sources aren't asked and Auto stops.
    Its data stays, for when it's on again.
    """
    person = await _other(session, person_id)
    person.disabled_at = (person.disabled_at or datetime.now(UTC)) if disabled else None
    if disabled:
        now = datetime.now(UTC)
        await session.execute(delete_(Session).where(Session.owner_id == person.id))
        await session.execute(delete_(ApiToken).where(ApiToken.owner_id == person.id))
        # Auto stops preparing for it.
        await session.execute(
            update(AutoRun)
            .where(AutoRun.owner_id == person.id, AutoRun.status.in_((*auto_repo.ACTIVE, "ready")))
            .values(status="stopped", finished_at=now)
        )
    await session.flush()
    return person


async def delete(session: AsyncSession, person_id: str) -> str:
    """The account and everything in it (every owned table cascades). Returns its id, for its files."""
    person = await _other(session, person_id)
    await session.delete(person)
    await session.flush()
    return person_id
