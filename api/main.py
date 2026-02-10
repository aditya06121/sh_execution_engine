from fastapi import FastAPI
from schemas import (
    ExecuteRequest,
    SubmitRequest,
    Response,
    Result,
)

app = FastAPI(title="Ephemeral Code Execution & Judging API")


@app.post("/execute", response_model=Response)
def execute_visible_tests(req: ExecuteRequest):
    """
    Dummy execute endpoint.
    Validates request via Pydantic.
    Does NOT execute code.
    """

    results = []

    for tc in req.test_cases:
        results.append(
            Result(
                input=tc.input,
                expected_output=tc.expected_output,
                actual_output=None,
                passed=False
            )
        )

    return Response(
        status="completed",
        results=results,
        stdout="",
        stderr=""
    )


@app.post("/submit")
def submit_hidden_tests(req: SubmitRequest):
    """
    Dummy submit endpoint.
    Validates request via Pydantic.
    Does NOT execute code.
    """

    return {
        "status": "completed",
        "passed": 0,
        "total": 0,
        "verdict": "accepted",
        "stderr": "",
        "duration_ms": 0
    }
