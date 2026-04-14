import asyncio
import logging

import redis.exceptions
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import ExecuteRequest, SubmitResponse, JobResultResponse
from jobqueue.job import enqueue, get_job_status, queue_depth
from execution.pipeline import ExecutionPipeline
from config.limits import FALLBACK_MAX_CONCURRENT

log = logging.getLogger(__name__)

app = FastAPI(title="Ephemeral Code Execution & Judging API")

# Used only when Redis is unavailable; prevents the fallback path from
# accepting unlimited concurrent executions and collapsing the host.
_fallback_sem = asyncio.Semaphore(FALLBACK_MAX_CONCURRENT)

# Exceptions that mean Redis is simply not reachable right now.
_REDIS_ERRORS = (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    ConnectionRefusedError,
    OSError,
)


# ---------------------------------------------------------------------------
# POST /execute
# ---------------------------------------------------------------------------

@app.post("/execute")
async def execute(req: ExecuteRequest):
    """
    Normal path  (Redis up)   → 202 + {job_id, status:"queued"}
                                Poll GET /result/{job_id} for the verdict.
    Fallback path (Redis down) → 200 + verdict payload directly (synchronous).
    """
    try:
        job_id = await enqueue(req.model_dump())
        return JSONResponse(
            status_code=202,
            content={"job_id": job_id, "status": "queued"},
        )

    except OverflowError:
        raise HTTPException(
            status_code=503,
            detail="Queue at capacity — try again shortly",
            headers={"Retry-After": "5"},
        )

    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable (%s), falling back to direct execution", exc)
        return await _execute_direct(req)


async def _execute_direct(req: ExecuteRequest) -> JSONResponse:
    """
    Synchronous fallback executed when Redis is down.
    Bounded by _fallback_sem so the host is not overwhelmed.
    """
    try:
        await asyncio.wait_for(_fallback_sem.acquire(), timeout=30)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Server busy — Redis is unavailable and the fallback queue is full",
            headers={"Retry-After": "10"},
        )

    try:
        pipeline = ExecutionPipeline(req.model_dump())
        result = await pipeline.execute()
        return JSONResponse(status_code=200, content=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        _fallback_sem.release()


# ---------------------------------------------------------------------------
# GET /result/{job_id}
# ---------------------------------------------------------------------------

@app.get("/result/{job_id}", response_model=JobResultResponse)
async def result(job_id: str):
    """
    status == "queued"  → waiting for a worker
    status == "running" → being executed now
    status == "done"    → finished; see the `result` field for the verdict
    """
    try:
        data = await get_job_status(job_id)
    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable when fetching result: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Result store unavailable — Redis is down",
        )

    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found — it may have expired (results live for 10 minutes)",
        )
    return data


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    try:
        depth = await queue_depth()
        return {"ok": True, "redis": "up", "queue_depth": depth}
    except _REDIS_ERRORS:
        return JSONResponse(
            status_code=200,
            content={"ok": True, "redis": "down", "fallback": "direct execution"},
        )
