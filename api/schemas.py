from pydantic import BaseModel,Field
from typing import List, Optional, Dict,Any,Literal

class ErrorResponse(BaseModel):
    status: Literal["error"]
    reason : str = Field(...,max_length= 256)
    class Config:
        extra="forbid"

class TestCase(BaseModel):
    input: Dict[str,Any]
    expected_output: Optional[Any]=None
    class Config:
        extra="forbid"

class ExecuteRequest(BaseModel):
    problem_id:Optional[str] = Field(None, max_length=20000)
    language:Literal[
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
    function_name: str = Field(...,min_length=1,max_length=64)
    code: str = Field(...,min_length=1,max_length=5000)
    test_cases: List[TestCase] = Field(..., min_items=1, max_items=20)


    class Config:
        extra = "forbid"

class Result(BaseModel):
    input: Dict[str, Any]
    expected_output: Optional[Any]
    actual_output: Optional[Any]
    passed: bool

    class Config:
        extra = "forbid"


class Response(BaseModel):
    status: Literal["completed","failed"]
    results: List[Result]
    stdout: Optional[str] = Field(None, max_length=1000)
    stderr: Optional[str] = Field(None, max_length=1000)

    class Config:
        extra = "forbid"

class SubmitRequest(BaseModel):
    problem_id: Optional[str] = Field(None, max_length=64)
    language: Literal[
        "python", "javascript", "c", "java", "kotlin",
        "go", "rust", "typescript", "cpp", "csharp"
    ]

    function_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
    )

    code: str = Field(..., min_length=1, max_length=5000)

    class Config:
        extra = "forbid"
