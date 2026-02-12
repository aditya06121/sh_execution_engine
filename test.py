from execution.pipeline import ExecutionPipeline

request = {
    "language": "python",
    "source_code": "def add(a,b): return a/b",
    "function_name": "add",
    "test_cases": [
        {"input": {"a": 2, "b": 2}, "expected_output": 4}
    ]
}

pipeline = ExecutionPipeline(request)
print(pipeline.execute())
