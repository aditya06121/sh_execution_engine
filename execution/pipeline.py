from execution.executor import ExecutorFactory
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)


class ExecutionPipeline:

    def __init__(self, request: dict):
        self.request = request
        self.executor = None

    def execute(self) -> dict:
        try:
            # Create executor
            self.executor = ExecutorFactory.get_executor(
                self.request["language"],
                self.request["source_code"],
                self.request["function_name"],
            )

            # Compile phase
            try:
                self.executor.compile()
            except CompileError as e:
                return {
                    "verdict": "compilation_error",
                    "error_message": str(e),
                }

            # Run tests
            for index, tc in enumerate(self.request["test_cases"]):
                try:
                    output = self.executor.run(tc["input"])
                except RuntimeExecutionError as e:
                    return {
                        "verdict": "runtime_error",
                        "failed_test_case_index": index,
                        "error_message": str(e),
                    }

                if output != tc["expected_output"]:
                    return {
                        "verdict": "wrong_answer",
                        "failed_test_case_index": index,
                    }

            return {
                "verdict": "accepted"
            }

        finally:
            if self.executor:
                self.executor.cleanup()
