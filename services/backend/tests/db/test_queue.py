"""The Postgres job queue: one claimer per job, priorities, leases, retries, and enqueuing with the transaction."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from apply.libs.jobs import Handler, Permanent, Worker, enqueue
from apply.store.sql.models import jobs


async def add(rt, kind="t.ok", **kwargs) -> str:
    async with rt.db.transaction() as session:
        return await enqueue(session, jobs, kind=kind, queue=kwargs.pop("queue", "default"), **kwargs)


async def row(rt, job_id):
    async with rt.db.engine.connect() as conn:
        return (await conn.execute(select(jobs).where(jobs.c.id == job_id))).one()


def recorder():
    ran: list[str] = []

    async def run(ctx):
        ran.append(ctx.payload.get("name", ctx.id))

    return ran, run


async def test_two_claimers_never_take_the_same_job(rt):
    ids = {await add(rt, payload={"n": i}) for i in range(30)}
    claims = await asyncio.gather(
        *(rt.queue.claim(queues=["default"], kinds=["t.ok"], limit=5, worker=f"w{i}", leases={}) for i in range(8))
    )
    taken = [job.id for batch in claims for job in batch]
    assert len(taken) == len(set(taken)) == 30
    assert set(taken) == ids


async def test_the_highest_priority_runs_first_then_the_oldest(rt):
    await add(rt, payload={"name": "background"}, priority=0)
    await add(rt, payload={"name": "click"}, priority=100)
    await add(rt, payload={"name": "background 2"}, priority=0)
    ran, run = recorder()
    await Worker(rt.queue, {"t.ok": Handler(run)}, queues=["default"]).run_until_idle()
    assert ran == ["click", "background", "background 2"]


async def test_a_job_waits_for_its_time_and_its_queue(rt):
    ran, run = recorder()
    await add(rt, payload={"name": "later"}, run_after=datetime.now(UTC) + timedelta(hours=1))
    await add(rt, payload={"name": "other queue"}, queue="llm")
    await Worker(rt.queue, {"t.ok": Handler(run)}, queues=["default"]).run_until_idle()
    assert ran == []


async def test_a_key_makes_a_waiting_job_unique(rt):
    first = await add(rt, key="doc-1")
    assert await add(rt, key="doc-1") is None
    await Worker(rt.queue, {"t.ok": Handler(recorder()[1])}, queues=["default"]).run_until_idle()
    assert (await row(rt, first)).status == "done"
    assert await add(rt, key="doc-1") is not None  # finished: the key is free again


async def test_a_job_is_enqueued_with_its_transaction_or_not_at_all(rt):
    with pytest.raises(RuntimeError):
        async with rt.db.transaction() as session:
            await enqueue(session, jobs, kind="t.ok", payload={"name": "rolled back"})
            raise RuntimeError("the change failed")
    assert (await rt.queue.counts())["pending"] == 0


async def test_failures_back_off_then_fail_for_good_and_call_the_give_up_hook(rt):
    given_up: list[str] = []

    async def boom(ctx):
        raise ValueError("model on fire")

    async def give_up(ctx):
        given_up.append(ctx.error)

    job_id = await add(rt, kind="t.boom", max_attempts=2)
    worker = Worker(rt.queue, {"t.boom": Handler(boom, on_give_up=give_up)}, queues=["default"])
    await worker.run_until_idle()
    first = await row(rt, job_id)
    assert first.status == "pending" and first.attempts == 1 and "model on fire" in first.last_error
    assert first.run_after > datetime.now(UTC) + timedelta(seconds=5)  # backed off
    async with rt.db.engine.begin() as conn:
        # The database's clock, not this machine's: the two can differ by a few milliseconds.
        await conn.execute(update(jobs).where(jobs.c.id == job_id).values(run_after=func.now() - timedelta(seconds=1)))
    await worker.run_until_idle()
    assert (await row(rt, job_id)).status == "failed"
    assert given_up and "model on fire" in given_up[0]


async def test_a_permanent_failure_is_not_retried(rt):
    async def nope(ctx):
        raise Permanent("bad payload")

    job_id = await add(rt, kind="t.nope", max_attempts=5)
    await Worker(rt.queue, {"t.nope": Handler(nope)}, queues=["default"]).run_until_idle()
    found = await row(rt, job_id)
    assert found.status == "failed" and found.attempts == 1


async def test_a_dead_workers_job_is_reclaimed_and_its_last_attempt_given_up(rt):
    given_up: list[str] = []
    job_id = await add(rt, max_attempts=2)
    [claimed] = await rt.queue.claim(queues=["default"], kinds=["t.ok"], limit=1, worker="dead", leases={})
    async with rt.db.engine.begin() as conn:  # the dead worker's lease runs out
        await conn.execute(update(jobs).values(locked_until=datetime.now(UTC) - timedelta(seconds=1)))
    ran, run = recorder()

    async def give_up(ctx):
        given_up.append(ctx.id)

    worker = Worker(rt.queue, {"t.ok": Handler(run, on_give_up=give_up)}, queues=["default"])
    await worker.run_until_idle()
    assert len(ran) == 1 and (await row(rt, job_id)).status == "done"
    # The dead worker coming back can't finish it a second time.
    assert not await rt.queue.finish(claimed, "dead")

    # Out of attempts while running: the hook runs.
    job_id = await add(rt, max_attempts=1)
    await rt.queue.claim(queues=["default"], kinds=["t.ok"], limit=1, worker="dead", leases={})
    async with rt.db.engine.begin() as conn:
        await conn.execute(
            update(jobs).where(jobs.c.id == job_id).values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
        )
    await worker.run_until_idle()
    assert (await row(rt, job_id)).status == "failed" and given_up == [job_id]


async def test_the_lease_is_kept_while_a_long_job_runs(rt):
    async def slow(ctx):
        await asyncio.sleep(1.2)

    job_id = await add(rt, kind="t.slow")
    worker = Worker(rt.queue, {"t.slow": Handler(slow, lease_seconds=0.6)}, queues=["default"])
    task = asyncio.create_task(worker.run_until_idle())
    await asyncio.sleep(0.9)
    running = await row(rt, job_id)
    assert running.status == "running" and running.locked_until > datetime.now(UTC)
    await task
    assert (await row(rt, job_id)).status == "done"


async def test_a_running_worker_wakes_on_notify_without_waiting_for_its_poll(rt):
    ran, run = recorder()
    worker = Worker(rt.queue, {"t.ok": Handler(run)}, queues=["default"], poll_seconds=30, listen_dsn=rt.db.dsn)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_forever(stop))
    await asyncio.sleep(0.5)  # listening, idle, next poll in 30 s
    await add(rt, payload={"name": "now"})
    for _ in range(100):
        if ran:
            break
        await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, 10)
    assert ran == ["now"]


async def test_concurrency_is_respected(rt):
    running = 0
    most = 0

    async def track(ctx):
        nonlocal running, most
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.05)
        running -= 1

    for _ in range(6):
        await add(rt, kind="t.track")
    worker = Worker(rt.queue, {"t.track": Handler(track)}, queues=["default"], concurrency=2, poll_seconds=0.05)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_forever(stop))
    for _ in range(100):
        if (await rt.queue.counts())["done"] == 6:
            break
        await asyncio.sleep(0.05)
    stop.set()
    await task
    assert most == 2


async def test_old_finished_jobs_are_pruned(rt):
    job_id = await add(rt)
    await Worker(rt.queue, {"t.ok": Handler(recorder()[1])}, queues=["default"]).run_until_idle()
    async with rt.db.engine.begin() as conn:
        await conn.execute(update(jobs).values(finished_at=datetime.now(UTC) - timedelta(days=30)))
    assert await rt.queue.prune(keep_days=14) == 1
    async with rt.db.engine.connect() as conn:
        assert (await conn.execute(select(jobs).where(jobs.c.id == job_id))).first() is None
