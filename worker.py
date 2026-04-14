"""
Execution worker — pull jobs from Redis and run them.

Usage:
    WORKER_CONCURRENCY=10 python worker.py

Each worker process runs WORKER_CONCURRENCY async slots.  To scale,
run multiple processes (or containers) pointing at the same Redis instance.
Each slot independently BRPOPs from the queue, so there is no central
coordination needed.
"""

import asyncio
import json
import logging
import os
import signal
import time

from jobqueue.redis_client import get_redis
from jobqueue.job import QUEUE_KEY, JOB_MAX_AGE, mark_done, mark_running
from execution.pipeline import ExecutionPipeline
from config.limits import WORKER_CONCURRENCY as _DEFAULT_CONCURRENCY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [pid=%(process)d] %(message)s",
)
log = logging.getLogger(__name__)

WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", str(_DEFAULT_CONCURRENCY)))
BRPOP_TIMEOUT = 2   # seconds; short so shutdown is responsive

_shutdown = False


def _on_signal(signum, frame):
    global _shutdown
    log.info(f"Signal {signum} received — finishing in-flight jobs then exiting")
    _shutdown = True


async def _process(job_data: str) -> None:
    try:
        job = json.loads(job_data)
    except Exception:
        log.error("Received malformed job JSON — discarding")
        return

    job_id: str = job.get("job_id", "unknown")
    payload: dict = job.get("payload", {})
    age: float = time.time() - job.get("enqueued_at", 0.0)

    if age > JOB_MAX_AGE:
        log.warning(f"job={job_id} sat in queue {age:.0f}s > {JOB_MAX_AGE}s limit, skipping")
        await mark_done(job_id, {
            "verdict": "error",
            "error_message": f"Job expired after {age:.0f}s in queue",
        })
        return

    await mark_running(job_id)
    log.info(f"job={job_id} started (waited {age:.1f}s in queue)")

    try:
        pipeline = ExecutionPipeline(payload)
        result = await pipeline.execute()
        await mark_done(job_id, result)
        log.info(f"job={job_id} done verdict={result.get('verdict')}")
    except ValueError as e:
        await mark_done(job_id, {"verdict": "error", "error_message": str(e)})
        log.warning(f"job={job_id} rejected: {e}")
    except Exception:
        log.exception(f"job={job_id} unexpected error")
        await mark_done(job_id, {
            "verdict": "error",
            "error_message": "Internal execution error",
        })


async def _slot(slot_id: int) -> None:
    """
    One async worker slot.  Loops forever pulling one job at a time from Redis
    until the shutdown flag is set and the queue is drained.
    """
    r = get_redis()
    log.info(f"Slot {slot_id} ready")

    while not _shutdown:
        try:
            item = await r.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT)
        except Exception as e:
            log.error(f"Slot {slot_id} Redis error: {e!r} — retrying in 1s")
            await asyncio.sleep(1)
            continue

        if item is None:
            # Timeout — loop back and check _shutdown
            continue

        _, job_data = item
        await _process(job_data)

    log.info(f"Slot {slot_id} exited")


async def _main() -> None:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    log.info(f"Starting worker with {WORKER_CONCURRENCY} concurrent slots")
    await asyncio.gather(
        *[_slot(i) for i in range(WORKER_CONCURRENCY)],
        return_exceptions=True,
    )
    log.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(_main())
