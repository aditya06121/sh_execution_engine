from fastapi import FastAPI, HTTPException

from .schemas import ExecuteRequest, SubmitResponse, JobResultResponse
from jobqueue.job import enqueue, get_job_status, queue_depth

app = FastAPI(title="Ephemeral Code Execution & Judging API")


@app.post("/execute", response_model=SubmitResponse, status_code=202)
async def execute(req: ExecuteRequest):
    """
    Enqueue a code execution job.  Returns immediately with a job_id.
    Poll GET /result/{job_id} to retrieve the verdict once ready.
    """
    try:
        job_id = await enqueue(req.model_dump())
    except OverflowError:
        raise HTTPException(
            status_code=503,
            detail="Queue at capacity — try again shortly",
            headers={"Retry-After": "5"},
        )
    return {"job_id": job_id, "status": "queued"}


@app.get("/result/{job_id}", response_model=JobResultResponse)
async def result(job_id: str):
    """
    Poll for the result of a previously submitted job.

    status == "queued"  → not yet picked up by a worker
    status == "running" → worker is executing it now
    status == "done"    → finished; check the `result` field for the verdict
    """
    data = await get_job_status(job_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found — it may have expired (results live for 10 minutes)",
        )
    return data


@app.get("/health")
async def health():
    depth = await queue_depth()
    return {"ok": True, "queue_depth": depth}
