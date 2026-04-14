import asyncio
import tempfile
import os
import json
import shutil

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
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_SECONDS,
)

from .js_wrapper import JS_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class JavaScriptExecutor(BaseExecutor):

    IMAGE_NAME = "js-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.file_path = None

    # -------------------------
    # Compile Phase (JS has no compilation)
    # -------------------------

    async def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)

        self.file_path = os.path.join(self.temp_dir, "main.js")

        wrapped_code = JS_WRAPPER_TEMPLATE.replace("{source_code}", self.code)

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
            raise RuntimeExecutionError("Failed to start execution container")
        self.container_id = stdout.decode().strip()

    # -------------------------
    # Run Phase
    # -------------------------

    async def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({"function_name": self.function_name, "input": test_input}).encode()

        exec_cmd = ["docker", "exec", "-i", self.container_id, "node", "main.js"]

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
            try:
                message = json.loads(stdout_str).get("error", "Runtime error")
            except Exception:
                message = stderr.decode() or "Runtime error"
            raise RuntimeExecutionError(message)

        try:
            return json.loads(stdout_str)["result"]
        except Exception:
            raise RuntimeExecutionError("Invalid output format")

    # -------------------------
    # Cleanup Phase
    # -------------------------

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
