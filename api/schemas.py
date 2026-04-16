from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Union


# -------------------------
# Base Config (Strict Mode)
# -------------------------

class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"


# -------------------------
# Test Case Model
# -------------------------

class TestCase(StrictBaseModel):
    input: Dict[str, Any]
    expected_output: Any


# -------------------------
# Execute Request Model
# -------------------------

class ExecuteRequest(StrictBaseModel):
    language: Literal[
        "python",
        "javascript",
        "c",
        "java",
        "kotlin",
        "go",
        "rust",
        "typescript",
        "cpp",
        "csharp",
    ]

    source_code: str = Field(..., min_length=1, max_length=5000)

    function_name: str = Field(..., min_length=1, max_length=100)

    test_cases: List[TestCase] = Field(
        ...,
        min_length=1,
        max_length=20,
    )


# -------------------------
# Execution Result Models
# -------------------------

class AcceptedResponse(StrictBaseModel):
    verdict: Literal["accepted"]
    actual_outputs: List[Any]


class WrongAnswerResponse(StrictBaseModel):
    verdict: Literal["wrong_answer"]
    failed_test_case_index: int = Field(..., ge=0)
    actual_output: Any
    expected_output: Any


class RuntimeErrorResponse(StrictBaseModel):
    verdict: Literal["runtime_error"]
    failed_test_case_index: int = Field(..., ge=0)
    error_message: str = Field(..., max_length=1000)


class CompilationErrorResponse(StrictBaseModel):
    verdict: Literal["compilation_error"]
    error_message: str = Field(..., max_length=1000)


class TimeoutResponse(StrictBaseModel):
    verdict: Literal["timeout"]
    failed_test_case_index: int = Field(..., ge=0)


class ErrorResponse(StrictBaseModel):
    verdict: Literal["error"]
    error_message: str


ExecuteResponse = Union[
    AcceptedResponse,
    WrongAnswerResponse,
    RuntimeErrorResponse,
    CompilationErrorResponse,
    TimeoutResponse,
    ErrorResponse,
]
