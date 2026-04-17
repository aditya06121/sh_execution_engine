import asyncio
import logging
import os
import shutil
import tempfile

import redis.exceptions
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import ExecuteRequest, RawExecuteRequest, RawExecuteResponse
from jobqueue.job import enqueue, get_job_status, queue_depth
from execution.pipeline import ExecutionPipeline
from config.limits import (
    FALLBACK_MAX_CONCURRENT,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
)
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots

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

_POLL_INTERVAL = 0.2   # seconds between internal result checks
_EXECUTE_TIMEOUT = 3600  # 1 hour — allows massive spikes to sit and wait gracefully


@app.post("/execute")
async def execute(req: ExecuteRequest):
    """
    Enqueues the job into Redis, waits internally for the worker to finish,
    then returns the verdict directly.  Clients make one request and get one
    response — no polling required.

    Fallback path (Redis down) → runs the job synchronously in-process.
    """
    try:
        job_id = await enqueue(req.model_dump())
    except OverflowError:
        raise HTTPException(
            status_code=503,
            detail="Queue at capacity — try again shortly",
            headers={"Retry-After": "5"},
        )
    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable (%s), falling back to direct execution", exc)
        return await _execute_direct(req)

    from jobqueue.job import wait_for_job_result
    # Internal wait using redis blpop — invisible to the caller
    try:
        result = await wait_for_job_result(job_id, timeout=_EXECUTE_TIMEOUT)
    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable while waiting for job %s: %s", job_id, exc)
        raise HTTPException(status_code=503, detail="Result store unavailable")

    if result is None:
        raise HTTPException(status_code=504, detail="Execution timed out")

    return JSONResponse(status_code=200, content=result)


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
# POST /execute/raw
# ---------------------------------------------------------------------------

@app.post("/execute/raw", response_model=RawExecuteResponse)
async def execute_raw(req: RawExecuteRequest):
    """
    Enqueues the job into Redis, waits internally for the worker to finish,
    then returns the verdict directly.  Clients make one request and get one
    response — no polling required.
    """
    payload = req.model_dump()
    payload["is_raw"] = True
    
    try:
        job_id = await enqueue(payload)
    except OverflowError:
        raise HTTPException(
            status_code=503,
            detail="Queue at capacity — try again shortly",
            headers={"Retry-After": "5"},
        )
    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable (%s), falling back to direct execution", exc)
        return await _execute_direct(req, is_raw=True)

    from jobqueue.job import wait_for_job_result
    try:
        result = await wait_for_job_result(job_id, timeout=_EXECUTE_TIMEOUT)
    except _REDIS_ERRORS as exc:
        log.warning("Redis unavailable while waiting for job %s: %s", job_id, exc)
        raise HTTPException(status_code=503, detail="Result store unavailable")

    if result is None:
        raise HTTPException(status_code=504, detail="Execution timed out")

    return JSONResponse(status_code=200, content=result)


async def _execute_direct(req, is_raw: bool = False) -> JSONResponse:
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
        payload = req.model_dump()
        payload["is_raw"] = is_raw
        pipeline = ExecutionPipeline(payload)
        result = await pipeline.execute()
        return JSONResponse(status_code=200, content=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        _fallback_sem.release()


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
