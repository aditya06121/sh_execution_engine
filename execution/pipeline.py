from execution.executor import ExecutorFactory
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)


class ExecutionPipeline:

    def __init__(self, request: dict):
        self.request = request
        self.executor = None

    async def execute(self) -> dict:
        try:
            self.executor = ExecutorFactory.get_executor(
                self.request["language"],
                self.request["source_code"],
                self.request["function_name"],
            )

            try:
                await self.executor.compile()
            except (CompileError, RuntimeExecutionError) as e:
                return {
                    "verdict": "compilation_error",
                    "error_message": str(e),
                }

            actual_outputs = []
            for index, tc in enumerate(self.request["test_cases"]):
                try:
                    output = await self.executor.run(tc["input"])
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
                import asyncio
                try:
                    # Run cleanup shielded so that even if the request/worker cancels,
                    # the docker rm -f command finishes successfully in the background.
                    await asyncio.shield(self.executor.cleanup())
                except asyncio.CancelledError:
                    pass
