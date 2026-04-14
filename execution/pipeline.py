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
            except (CompileError, RuntimeExecutionError) as e:
                return {
                    "verdict": "compilation_error",
                    "error_message": str(e),
                }

            # Run tests
            actual_outputs = []
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
                        "actual_output": output,
                        "expected_output": tc["expected_output"],
                    }

                actual_outputs.append(output)

            return {
                "verdict": "accepted",
                "actual_outputs": actual_outputs,
            }

        finally:
            if self.executor:
                self.executor.cleanup()
