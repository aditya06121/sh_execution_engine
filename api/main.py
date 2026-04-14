import asyncio

from fastapi import FastAPI, HTTPException

from .schemas import ExecuteRequest, ExecuteResponse
from execution.pipeline import ExecutionPipeline
from config.limits import MAX_CONCURRENT_EXECUTIONS


app = FastAPI(title="Ephemeral Code Execution & Judging API")

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXECUTIONS)


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):

    if _semaphore.locked():
        raise HTTPException(
            status_code=503,
            detail="Server is at capacity, please try again later",
        )

    async with _semaphore:
        loop = asyncio.get_running_loop()
        pipeline = ExecutionPipeline(req.model_dump())
        try:
            return await loop.run_in_executor(None, pipeline.execute)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Unsupported language",
            )
