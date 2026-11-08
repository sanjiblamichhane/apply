"""
A job queue in Postgres: no Redis, no broker, one database.

- **Enqueue** inside the transaction that made the change, so a job exists if and only if the change committed.
  A ``NOTIFY`` in the same transaction wakes idle workers the moment it commits.
- **Claim** in one short transaction with ``FOR UPDATE SKIP LOCKED``: several workers never take the same job,
  and no lock is held while a job runs. A claimed job has a lease (``locked_until``) its worker keeps extending
  while it works; a lease that runs out (the worker died) puts the job back, or fails it once it has had its
  attempts.
- **Finish** and **fail** only while the lease is still the worker's, so a job reclaimed from a stalled worker
  can't be finished twice.
- A ``key`` makes a job unique while it is waiting or running: enqueuing the same kind and key again is a no-op.

Delivery is at least once: a handler must be safe to run twice (check before acting).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from ulid import ULID

PENDING, RUNNING, DONE, FAILED = "pending", "running", "done", "failed"
STATUSES = (PENDING, RUNNING, DONE, FAILED)
BACKOFF = (10, 60, 300, 1800)  # seconds before trying a failed job again
CHANNEL = "apply_jobs"


def jobs_table(metadata: MetaData, name: str = "jobs") -> Table:
    """The queue's table, in the caller's metadata (so its migrations own it)."""
    return Table(
        name,
        metadata,
        Column("id", String(26), primary_key=True),
        Column("kind", String(100), nullable=False),
        Column("queue", String(40), nullable=False, server_default="default"),
        Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        Column("priority", Integer, nullable=False, server_default="0"),
        Column("status", String(12), nullable=False, server_default=PENDING),
        Column("run_after", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("attempts", Integer, nullable=False, server_default="0"),
        Column("max_attempts", Integer, nullable=False, server_default="3"),
        Column("locked_by", String(200)),
        Column("locked_until", DateTime(timezone=True)),
        Column("last_error", Text),
        Column("key", String(200)),
        Column("owner_id", String(26)),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
        Column("finished_at", DateTime(timezone=True)),
        Index(f"ix_{name}_claim", "queue", "status", "priority", "run_after"),
        Index(f"ix_{name}_lease", "status", "locked_until"),
        Index(f"ix_{name}_finished", "finished_at"),
        Index(
            f"uq_{name}_kind_key_open",
            "kind",
            "key",
            unique=True,
            postgresql_where=text("key IS NOT NULL AND status IN ('pending', 'running')"),
        ),
    )


@dataclass(frozen=True)
class Claimed:
    id: str
    kind: str
    queue: str
    payload: dict[str, Any]
    attempts: int  # including this one
    max_attempts: int
    owner_id: str | None
    last_error: str | None = None


async def enqueue(
    session: AsyncSession | AsyncConnection,
    table: Table,
    *,
    kind: str,
    payload: dict[str, Any] | None = None,
    queue: str = "default",
    priority: int = 0,
    run_after: datetime | None = None,
    max_attempts: int = 3,
    key: str | None = None,
    owner_id: str | None = None,
    channel: str = CHANNEL,
) -> str | None:
    """Add a job. Returns its id, or None when a job of this kind and key is already waiting or running."""
    values: dict[str, Any] = {
        "id": str(ULID()),
        "kind": kind,
        "queue": queue,
        "payload": payload or {},
        "priority": priority,
        "max_attempts": max_attempts,
        "key": key,
        "owner_id": owner_id,
    }
    if run_after is not None:
        values["run_after"] = run_after
    stmt = insert(table).values(**values)
    if key is not None:
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["kind", "key"], index_where=text("key IS NOT NULL AND status IN ('pending', 'running')")
        )
    job_id = (await session.execute(stmt.returning(table.c.id))).scalar_one_or_none()
    if job_id is not None:
        await session.execute(select(func.pg_notify(channel, queue)))
    return job_id


class Queue:
    def __init__(self, engine: AsyncEngine, table: Table):
        self.engine = engine
        self.table = table

    async def claim(
        self, *, queues: list[str], kinds: list[str], limit: int, worker: str, leases: dict[str, float]
    ) -> list[Claimed]:
        """Take up to ``limit`` due jobs, the highest priority first."""
        t = self.table
        async with self.engine.begin() as conn:
            rows = (
                await conn.execute(
                    select(t.c.id, t.c.kind)
                    .where(
                        t.c.status == PENDING, t.c.run_after <= func.now(), t.c.queue.in_(queues), t.c.kind.in_(kinds)
                    )
                    .order_by(t.c.priority.desc(), t.c.run_after, t.c.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            claimed: list[Claimed] = []
            for row in rows:
                lease = leases.get(row.kind, 300.0)
                got = (
                    await conn.execute(
                        update(t)
                        .where(t.c.id == row.id)
                        .values(
                            status=RUNNING,
                            locked_by=worker,
                            attempts=t.c.attempts + 1,
                            locked_until=func.now() + func.make_interval(0, 0, 0, 0, 0, 0, lease),
                        )
                        .returning(
                            t.c.id,
                            t.c.kind,
                            t.c.queue,
                            t.c.payload,
                            t.c.attempts,
                            t.c.max_attempts,
                            t.c.owner_id,
                            t.c.last_error,
                        )
                    )
                ).one()
                claimed.append(Claimed(*got))
        return claimed

    async def extend(self, job_id: str, worker: str, seconds: float) -> bool:
        """Keep the lease while the job runs. False: it is no longer this worker's."""
        t = self.table
        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(t)
                .where(t.c.id == job_id, t.c.locked_by == worker, t.c.status == RUNNING)
                .values(locked_until=func.now() + func.make_interval(0, 0, 0, 0, 0, 0, seconds))
            )
        return bool(result.rowcount)

    async def finish(self, job: Claimed, worker: str) -> bool:
        t = self.table
        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(t)
                .where(*self._mine(job, worker))
                .values(status=DONE, finished_at=func.now(), locked_by=None, locked_until=None, last_error=None)
            )
        return bool(result.rowcount)

    async def fail(self, job: Claimed, worker: str, error: str, *, retry: bool) -> str | None:
        """Back off and try again later, or fail for good. Returns the new status (None: not this worker's)."""
        t = self.table
        give_up = not retry or job.attempts >= job.max_attempts
        delay = BACKOFF[min(job.attempts - 1, len(BACKOFF) - 1)]
        values: dict[str, Any] = {"locked_by": None, "locked_until": None, "last_error": error[:4000]}
        if give_up:
            values |= {"status": FAILED, "finished_at": func.now()}
        else:
            values |= {"status": PENDING, "run_after": func.now() + func.make_interval(0, 0, 0, 0, 0, 0, delay)}
        async with self.engine.begin() as conn:
            result = await conn.execute(update(t).where(*self._mine(job, worker)).values(**values))
        if not result.rowcount:
            return None
        return FAILED if give_up else PENDING

    async def reclaim(self, kinds: list[str]) -> list[Claimed]:
        """
        Jobs whose worker stopped renewing its lease: back to waiting if they have attempts left, failed if not.
        Returns the failed ones, for their give-up hooks.
        """
        t = self.table
        expired = and_(t.c.status == RUNNING, t.c.locked_until < func.now(), t.c.kind.in_(kinds))
        async with self.engine.begin() as conn:
            await conn.execute(
                update(t)
                .where(expired, t.c.attempts < t.c.max_attempts)
                .values(
                    status=PENDING,
                    locked_by=None,
                    locked_until=None,
                    run_after=func.now(),
                    last_error="The worker running this job stopped; trying again.",
                )
            )
            failed = (
                await conn.execute(
                    update(t)
                    .where(expired, t.c.attempts >= t.c.max_attempts)
                    .values(
                        status=FAILED,
                        locked_by=None,
                        locked_until=None,
                        finished_at=func.now(),
                        last_error="The worker running this job stopped, and it has had all its attempts.",
                    )
                    .returning(
                        t.c.id,
                        t.c.kind,
                        t.c.queue,
                        t.c.payload,
                        t.c.attempts,
                        t.c.max_attempts,
                        t.c.owner_id,
                        t.c.last_error,
                    )
                )
            ).all()
        return [Claimed(*row) for row in failed]

    async def prune(self, *, keep_days: int = 14) -> int:
        """Delete finished jobs older than ``keep_days``."""
        t = self.table
        async with self.engine.begin() as conn:
            result = await conn.execute(
                t.delete().where(
                    t.c.status.in_((DONE, FAILED)),
                    t.c.finished_at < func.now() - func.make_interval(0, 0, 0, keep_days),
                )
            )
        return result.rowcount or 0

    async def counts(self) -> dict[str, int]:
        t = self.table
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(t.c.status, func.count()).group_by(t.c.status))).all()
        return {status: 0 for status in STATUSES} | {row[0]: row[1] for row in rows}

    def _mine(self, job: Claimed, worker: str) -> list[Any]:
        t = self.table
        return [t.c.id == job.id, t.c.locked_by == worker, t.c.status == RUNNING]
