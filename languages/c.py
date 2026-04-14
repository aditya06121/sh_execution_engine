import asyncio
import tempfile
import os
import json
import shutil
import re

from execution.base import BaseExecutor
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
)

from execution.sandbox_paths import (
    build_host_temp_dir,
    get_sandbox_roots,
)

from config.limits import (
    EXECUTION_TIMEOUT_SECONDS,
    COMPILATION_TIMEOUT_SECONDS,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_SECONDS,
)

from .c_wrapper import C_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class CExecutor(BaseExecutor):

    IMAGE_NAME = "cpp-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.file_path = None

    # ==========================================================
    # Compile Phase
    # ==========================================================

    async def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)

        wrapped_code = self._generate_wrapper()

        if "__PLACEHOLDER__" in wrapped_code:
            raise CompileError("Wrapper placeholder replacement failed")

        self.file_path = os.path.join(self.temp_dir, "solution.cpp")

        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        run_cmd = [
            "docker", "run",
            "-d", "--rm",
            "--memory", DOCKER_MEMORY_LIMIT,
            "--memory-swap", DOCKER_MEMORY_SWAP,
            "--cpus", DOCKER_CPU_LIMIT,
            "--pids-limit", DOCKER_PIDS_LIMIT,
            "--ulimit", f"nofile={DOCKER_NOFILE_LIMIT}:{DOCKER_NOFILE_LIMIT}",
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-v", f"{self.host_temp_dir}:/app",
            "-w", "/app",
            self.IMAGE_NAME,
            "sleep", str(CONTAINER_SLEEP_SECONDS),
        ]

        proc = await asyncio.create_subprocess_exec(*run_cmd, stdout=PIPE, stderr=PIPE)
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeExecutionError("Failed to start container")
        self.container_id = stdout.decode().strip()

        compile_cmd = [
            "docker", "exec", self.container_id,
            "g++", "solution.cpp", "-O2", "-std=c++20", "-o", "solution",
        ]

        proc = await asyncio.create_subprocess_exec(*compile_cmd, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMPILATION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise CompileError("Compilation timed out")

        if proc.returncode != 0:
            raise CompileError(stderr.decode())

    # ==========================================================
    # Run Phase
    # ==========================================================

    async def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps(test_input).encode()

        exec_cmd = ["docker", "exec", "-i", self.container_id, "./solution"]

        proc = await asyncio.create_subprocess_exec(*exec_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(payload), timeout=EXECUTION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeExecutionError("Execution timed out")

        stdout_str = stdout.decode()

        if len(stdout_str.encode("utf-8")) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if proc.returncode != 0:
            raise RuntimeExecutionError(
                stderr.decode().strip() or stdout_str.strip() or "Runtime error"
            )

        try:
            return json.loads(stdout_str.strip())
        except Exception:
            raise RuntimeExecutionError("Invalid JSON output")

    # ==========================================================
    # Cleanup
    # ==========================================================

    async def cleanup(self):

        if self.container_id:
            proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", self.container_id,
                stdout=DEVNULL, stderr=DEVNULL,
            )
            await proc.wait()
            self.container_id = None

        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
            self.host_temp_dir = None

    # ==========================================================
    # Wrapper Generator
    # ==========================================================

    def _generate_wrapper(self):

        return_type, params = self._parse_signature()

        param_deserialization = []
        param_names = []

        for param_type, param_name in params:

            clean_type = param_type.replace("const", "").strip()

            if clean_type == "int":
                param_deserialization.append(f'int {param_name} = j["{param_name}"];')

            elif clean_type == "long":
                param_deserialization.append(f'long {param_name} = j["{param_name}"];')

            elif clean_type == "double":
                param_deserialization.append(f'double {param_name} = j["{param_name}"];')

            elif clean_type == "char*":
                param_deserialization.append(f'string {param_name}_tmp = j["{param_name}"];')
                param_deserialization.append(f'char* {param_name} = (char*){param_name}_tmp.c_str();')

            else:
                raise CompileError(f"Unsupported C type: {clean_type}")

            param_names.append(param_name)

        return_serialization = "output = result;"

        wrapper = C_WRAPPER_TEMPLATE \
            .replace(
                "__FUNCTION_SIGNATURE_PLACEHOLDER__",
                f"{return_type} {self.function_name}({', '.join([f'{t} {n}' for t, n in params])});",
            ) \
            .replace(
                "__PARAMETER_DESERIALIZATION_PLACEHOLDER__",
                "\n        ".join(param_deserialization),
            ) \
            .replace(
                "__FUNCTION_CALL_PLACEHOLDER__",
                f"auto result = {self.function_name}({', '.join(param_names)});",
            ) \
            .replace("__RETURN_SERIALIZATION_PLACEHOLDER__", return_serialization) \
            .replace("__USER_CODE_PLACEHOLDER__", self.code)

        return wrapper

    # ==========================================================
    # Signature Parser
    # ==========================================================

    def _parse_signature(self):

        pattern = rf'([^\s]+(?:\s*\*?)?)\s+{self.function_name}\s*\((.*?)\)'
        match = re.search(pattern, self.code, re.DOTALL)

        if not match:
            raise CompileError("Could not parse function signature")

        return_type = match.group(1).strip()
        params_str = match.group(2).strip()

        params = []

        if params_str:
            raw_params = [p.strip() for p in params_str.split(",")]

            for p in raw_params:
                parts = p.split()
                param_name = parts[-1].replace("&", "").replace("*", "")
                param_type = " ".join(parts[:-1])
                params.append((param_type.strip(), param_name.strip()))

        return return_type, params
