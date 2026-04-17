import os
import shutil
import tempfile
import asyncio

from execution.executor import ExecutorFactory
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots
from config.limits import (
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
)


class ExecutionPipeline:

    def __init__(self, request: dict):
        self.request = request
        self.executor = None
        self.is_raw = request.get("is_raw", False)

    async def _execute_raw(self) -> dict:
        container_root, host_root = get_sandbox_roots()
        temp_dir = tempfile.mkdtemp(dir=container_root)
        host_temp_dir = build_host_temp_dir(host_root, temp_dir)

        language = self.request["language"]
        source_code = self.request["source_code"]
        args = self.request.get("args", [])
        stdin = self.request.get("stdin", "")

        LANG_CONFIG = {
            "python": {"image": "python-sandbox:latest", "ext": ".py", "cmd": ["python3", "main.py"]},
            "javascript": {"image": "js-sandbox:latest", "ext": ".js", "cmd": ["node", "main.js"]},
            "c": {"image": "c-sandbox:latest", "ext": ".c", "cmd": ["sh", "-c", 'gcc -O2 main.c -o main && ./main "$@"', "sh"]},
            "cpp": {"image": "cpp-sandbox:latest", "ext": ".cpp", "cmd": ["sh", "-c", 'g++ -O2 main.cpp -o main && ./main "$@"', "sh"]},
            "java": {"image": "java-sandbox:latest", "ext": ".java", "cmd": ["sh", "-c", 'javac Main.java && java Main "$@"', "sh"]},
            "kotlin": {"image": "kotlin-sandbox:latest", "ext": ".kt", "cmd": ["sh", "-c", 'kotlinc main.kt -include-runtime -d main.jar && java -jar main.jar "$@"', "sh"]},
            "go": {"image": "go-sandbox:latest", "ext": ".go", "cmd": ["sh", "-c", 'go build -o main main.go && ./main "$@"', "sh"]},
            "rust": {"image": "rust-sandbox:latest", "ext": ".rs", "cmd": ["sh", "-c", 'rustc main.rs -o main && ./main "$@"', "sh"]},
            "typescript": {"image": "ts-sandbox:latest", "ext": ".ts", "cmd": ["sh", "-c", 'tsc main.ts && node main.js "$@"', "sh"]},
            "csharp": {"image": "csharp-sandbox:latest", "ext": ".cs", "cmd": ["sh", "-c", 'echo \'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>disable</Nullable></PropertyGroup></Project>\' > main.csproj && dotnet run -- "$@"', "sh"]},
        }

        config = LANG_CONFIG[language]
        file_name = f"main{config['ext']}"
        if language == "java":
            file_name = "Main.java"

        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, "w") as f:
            f.write(source_code)

        run_cmd = [
            "docker", "run", "-i", "--rm",
            "--memory", DOCKER_MEMORY_LIMIT,
            "--memory-swap", DOCKER_MEMORY_SWAP,
            "--cpus", DOCKER_CPU_LIMIT,
            "--pids-limit", DOCKER_PIDS_LIMIT,
            "--ulimit", f"nofile={DOCKER_NOFILE_LIMIT}:{DOCKER_NOFILE_LIMIT}",
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-v", f"{host_temp_dir}:/app",
            "-w", "/app",
            config["image"]
        ] + config["cmd"] + args

        proc = await asyncio.create_subprocess_exec(
            *run_cmd,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            input_bytes = stdin.encode('utf-8') if stdin else None
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_bytes), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"stdout": "", "stderr": "Execution timed out", "exit_code": 124}

        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "stdout": stdout.decode(errors='replace')[:10000],
            "stderr": stderr.decode(errors='replace')[:10000],
            "exit_code": proc.returncode
        }

    async def execute(self) -> dict:
        if self.is_raw:
            return await self._execute_raw()

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
