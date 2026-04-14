import json
import time
import uuid

from jobqueue.redis_client import get_redis

QUEUE_KEY = "exec:queue"
JOB_PREFIX = "exec:job:"

RESULT_TTL = 600     # seconds — clients have 10 min to poll before result expires
JOB_MAX_AGE = 300    # seconds — worker skips a job that sat in queue longer than this
MAX_QUEUE_DEPTH = 10_000  # refuse new jobs above this; keeps memory bounded


async def enqueue(payload: dict) -> str:
    r = get_redis()

    depth = await r.llen(QUEUE_KEY)
    if depth >= MAX_QUEUE_DEPTH:
        raise OverflowError("Queue at capacity")

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "payload": payload,
        "enqueued_at": time.time(),
    }

    pipe = r.pipeline()
    pipe.lpush(QUEUE_KEY, json.dumps(job))
    pipe.set(f"{JOB_PREFIX}{job_id}", json.dumps({"status": "queued"}), ex=RESULT_TTL)
    await pipe.execute()

    return job_id


async def mark_running(job_id: str) -> None:
    r = get_redis()
    await r.set(
        f"{JOB_PREFIX}{job_id}",
        json.dumps({"status": "running"}),
        ex=RESULT_TTL,
    )


async def mark_done(job_id: str, result: dict) -> None:
    r = get_redis()
    await r.set(
        f"{JOB_PREFIX}{job_id}",
        json.dumps({"status": "done", "result": result}),
        ex=RESULT_TTL,
    )


async def get_job_status(job_id: str) -> dict | None:
    r = get_redis()
    val = await r.get(f"{JOB_PREFIX}{job_id}")
    if val is None:
        return None
    return json.loads(val)


async def queue_depth() -> int:
    r = get_redis()
    return await r.llen(QUEUE_KEY)
