import asyncio

from fastapi import FastAPI, HTTPException

from .schemas import ExecuteRequest, ExecuteResponse
from execution.pipeline import ExecutionPipeline
from config.limits import MAX_CONCURRENT_EXECUTIONS, QUEUE_TIMEOUT_SECONDS


app = FastAPI(title="Ephemeral Code Execution & Judging API")

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXECUTIONS)


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    try:
        await asyncio.wait_for(_semaphore.acquire(), timeout=QUEUE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Queue timeout: server is too busy, please try again later",
        )

    try:
        pipeline = ExecutionPipeline(req.model_dump())
        try:
            return await pipeline.execute()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Unsupported language",
            )
    finally:
        _semaphore.release()
