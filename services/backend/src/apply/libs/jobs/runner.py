"""
Running jobs: claim what's due, run each with its handler, keep its lease while it runs, and record the outcome.

    worker = Worker(queue, {"document.generate": Handler(write_document, lease_seconds=240)},
                    queues=["llm"], concurrency=1, listen_dsn=dsn)
    await worker.run_forever(stop_event)      # or, in tests: await worker.run_until_idle()

A handler raising ``Permanent`` fails its job at once; any other exception is retried with backoff up to the job's
``max_attempts``. When a job fails for good (its last attempt raised, or its worker died on the last attempt), the
handler's ``on_give_up`` runs, so whatever the job stood for never stays "in progress" for ever.
"""

import asyncio
import contextlib
import logging
import os
import socket
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .queue import CHANNEL, FAILED, Claimed, Queue

logger = logging.getLogger("apply.libs.jobs")


class Permanent(Exception):
    """A failure that trying again won't fix: fail the job now."""


@dataclass(frozen=True)
class JobContext:
    id: str
    kind: str
    payload: dict[str, Any]
    attempt: int
    max_attempts: int
    owner_id: str | None
    error: str | None = None  # on give-up: why

    @property
    def last_attempt(self) -> bool:
        return self.attempt >= self.max_attempts


Run = Callable[[JobContext], Awaitable[None]]


@dataclass(frozen=True)
class Periodic:
    """Something the running worker does every ``seconds`` (the scheduler's tick), outside any job."""

    seconds: float
    run: Callable[[], Awaitable[object]]


@dataclass(frozen=True)
class Handler:
    run: Run
    on_give_up: Run | None = None
    lease_seconds: float = 300.0


@dataclass
class Stats:
    done: int = 0
    retried: int = 0
    failed: int = 0
    reclaimed_failed: int = 0
    kinds: dict[str, int] = field(default_factory=dict)


def _context(job: Claimed, error: str | None = None) -> JobContext:
    return JobContext(
        id=job.id,
        kind=job.kind,
        payload=job.payload,
        attempt=job.attempts,
        max_attempts=job.max_attempts,
        owner_id=job.owner_id,
        error=error,
    )


class Worker:
    def __init__(
        self,
        queue: Queue,
        handlers: dict[str, Handler],
        *,
        queues: list[str],
        concurrency: int = 1,
        name: str | None = None,
        poll_seconds: float = 2.0,
        listen_dsn: str | None = None,
        channel: str = CHANNEL,
        prune_every_seconds: float = 3600.0,
        periodic: list[Periodic] | None = None,
    ):
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self.queue = queue
        self.handlers = handlers
        self.queues = queues
        self.concurrency = concurrency
        self.name = name or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self.poll_seconds = poll_seconds
        self.listen_dsn = listen_dsn
        self.channel = channel
        self.periodic = periodic or []
        self.prune_every_seconds = prune_every_seconds
        self.stats = Stats()
        self._wake = asyncio.Event()
        self._leases = {kind: h.lease_seconds for kind, h in handlers.items()}

    @property
    def kinds(self) -> list[str]:
        return list(self.handlers)

    # ── one job ──────────────────────────────────────────────────────────────

    async def _run(self, job: Claimed) -> None:
        handler = self.handlers[job.kind]
        keeper = asyncio.create_task(self._keep_lease(job, handler.lease_seconds))
        error: BaseException | None = None
        try:
            await handler.run(_context(job))
        except asyncio.CancelledError:
            keeper.cancel()
            raise  # shutting down: the lease runs out and the job is reclaimed
        except Exception as exc:
            error = exc
        finally:
            keeper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keeper

        self.stats.kinds[job.kind] = self.stats.kinds.get(job.kind, 0) + 1
        if error is None:
            await self.queue.finish(job, self.name)
            self.stats.done += 1
            return
        message = f"{type(error).__name__}: {error}"
        retry = not isinstance(error, Permanent)
        logger.warning(
            "jobs: %s (%s) failed, attempt %d of %d: %s",
            job.kind,
            job.id,
            job.attempts,
            job.max_attempts,
            message,
            exc_info=not isinstance(error, Permanent),
        )
        status = await self.queue.fail(job, self.name, message, retry=retry)
        if status == FAILED:
            self.stats.failed += 1
            await self._give_up(job, message)
        elif status is not None:
            self.stats.retried += 1

    async def _give_up(self, job: Claimed, error: str) -> None:
        hook = self.handlers[job.kind].on_give_up if job.kind in self.handlers else None
        if hook is None:
            return
        try:
            await hook(_context(job, error))
        except Exception:
            logger.exception("jobs: the give-up hook for %s (%s) failed", job.kind, job.id)

    async def _keep_lease(self, job: Claimed, lease: float) -> None:
        while True:
            await asyncio.sleep(max(lease / 3, 0.5))
            try:
                if not await self.queue.extend(job.id, self.name, lease):
                    logger.warning("jobs: lost the lease on %s (%s)", job.kind, job.id)
                    return
            except Exception:
                logger.warning("jobs: could not renew the lease on %s (%s)", job.kind, job.id, exc_info=True)

    # ── the loop ─────────────────────────────────────────────────────────────

    async def _reclaim(self) -> None:
        for job in await self.queue.reclaim(self.kinds):
            self.stats.reclaimed_failed += 1
            await self._give_up(job, job.last_error or "The worker running this job stopped.")

    async def run_until_idle(self, *, max_rounds: int = 1000) -> Stats:
        """Run everything due now (and whatever that enqueues), then return. For tests and `--once`."""
        for _round in range(max_rounds):
            await self._reclaim()
            claimed = await self.queue.claim(
                queues=self.queues, kinds=self.kinds, limit=self.concurrency, worker=self.name, leases=self._leases
            )
            if not claimed:
                return self.stats
            await asyncio.gather(*(self._run(job) for job in claimed))
        return self.stats

    async def run_forever(self, stop: asyncio.Event) -> Stats:
        listener = await self._listen()
        running: set[asyncio.Task[None]] = set()
        loop = asyncio.get_running_loop()
        last_prune = 0.0
        last_periodic = [float("-inf")] * len(self.periodic)
        try:
            while not stop.is_set():
                try:
                    await self._reclaim()
                    free = self.concurrency - len(running)
                    if free > 0:
                        for job in await self.queue.claim(
                            queues=self.queues, kinds=self.kinds, limit=free, worker=self.name, leases=self._leases
                        ):
                            task = asyncio.create_task(self._run(job), name=f"job:{job.kind}:{job.id}")
                            running.add(task)
                            task.add_done_callback(running.discard)
                    for n, periodic in enumerate(self.periodic):
                        if loop.time() - last_periodic[n] >= periodic.seconds:
                            last_periodic[n] = loop.time()
                            try:
                                await periodic.run()
                            except Exception:
                                logger.exception("jobs: a periodic task failed; it runs again next time")
                    if loop.time() - last_prune > self.prune_every_seconds:
                        last_prune = loop.time()
                        await self.queue.prune()
                    if self.listen_dsn and (listener is None or listener.is_closed()):
                        listener = await self._listen()
                except Exception:
                    logger.exception("jobs: the worker loop hit an error; carrying on")
                    await asyncio.sleep(self.poll_seconds)
                self._wake.clear()
                waits: list[asyncio.Future[Any]] = [
                    asyncio.ensure_future(self._wake.wait()),
                    asyncio.ensure_future(stop.wait()),
                ]
                if running:  # a slot freeing up is a reason to look again
                    waits.append(asyncio.ensure_future(asyncio.wait(set(running), return_when=asyncio.FIRST_COMPLETED)))
                _done, pending = await asyncio.wait(
                    waits, timeout=self.poll_seconds, return_when=asyncio.FIRST_COMPLETED
                )
                for fut in pending:
                    fut.cancel()
        finally:
            if running:
                # Let what's running finish (a resume takes seconds); a second Ctrl+C cancels.
                await asyncio.gather(*running, return_exceptions=True)
            if listener is not None:
                with contextlib.suppress(Exception):
                    await listener.close()
        return self.stats

    async def _listen(self) -> Any:
        """LISTEN for new jobs, so an idle worker starts one the moment it's enqueued (polling is the safety net)."""
        if not self.listen_dsn:
            return None
        try:
            import asyncpg

            conn = await asyncpg.connect(self.listen_dsn)

            def wake(_conn: Any, _pid: int, _channel: str, payload: str) -> None:
                if payload in self.queues:
                    self._wake.set()

            await conn.add_listener(self.channel, wake)
            conn.add_termination_listener(lambda _c: logger.warning("jobs: LISTEN connection closed; polling"))
            return conn
        except Exception:
            logger.warning("jobs: could not LISTEN for new jobs; polling every %.1fs", self.poll_seconds, exc_info=True)
            return None
