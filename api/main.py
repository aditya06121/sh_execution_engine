from fastapi import FastAPI, HTTPException
from .schemas import ExecuteRequest, ExecuteResponse
from execution.pipeline import ExecutionPipeline


app = FastAPI(title="Ephemeral Code Execution & Judging API")


@app.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):

    try:
        pipeline = ExecutionPipeline(req.model_dump())
        return pipeline.execute()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language"
        )
