from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Union


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
        min_items=1,
        max_items=20
    )


# -------------------------
# Response Models
# -------------------------

class AcceptedResponse(StrictBaseModel):
    verdict: Literal["accepted"]


class WrongAnswerResponse(StrictBaseModel):
    verdict: Literal["wrong_answer"]
    failed_test_case_index: int = Field(..., ge=0)


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



# -------------------------
# Unified Response Type
# -------------------------

ExecuteResponse = Union[
    AcceptedResponse,
    WrongAnswerResponse,
    RuntimeErrorResponse,
    CompilationErrorResponse,
    TimeoutResponse
]
