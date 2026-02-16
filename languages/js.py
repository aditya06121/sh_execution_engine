import subprocess
import tempfile
import os
import json
import shutil

from execution.base import BaseExecutor
from execution.exceptions import (
    CompileError,
    RuntimeExecutionError,
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

    def compile(self):

        container_sandbox_root = "/sandbox"
        host_sandbox_root = os.environ.get("HOST_SANDBOX_ROOT")

        if not host_sandbox_root:
            raise RuntimeExecutionError("HOST_SANDBOX_ROOT not set")

        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        folder_name = os.path.basename(self.temp_dir)
        self.host_temp_dir = os.path.join(host_sandbox_root, folder_name)

        # Write wrapped JS file
        self.file_path = os.path.join(self.temp_dir, "main.js")

        wrapped_code = JS_WRAPPER_TEMPLATE.replace(
            "{source_code}", self.code
        )

        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        # Start sandbox container
        run_cmd = [
            "docker", "run",
            "-d",
            "--rm",

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
            "sleep", str(CONTAINER_SLEEP_SECONDS)
        ]

        try:
            self.container_id = subprocess.check_output(run_cmd).decode().strip()
        except subprocess.CalledProcessError:
            raise RuntimeExecutionError("Failed to start execution container")

    # -------------------------
    # Run Phase
    # -------------------------

    def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps({
            "function_name": self.function_name,
            "input": test_input
        })

        exec_cmd = [
            "docker", "exec",
            "-i",
            self.container_id,
            "node", "main.js"
        ]

        try:
            process = subprocess.run(
                exec_cmd,
                input=payload,
                text=True,
                capture_output=True,
                timeout=EXECUTION_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            raise RuntimeExecutionError("Execution timed out")

        # Enforce stdout size limit
        if len(process.stdout.encode("utf-8")) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if process.returncode != 0:
            try:
                error_json = json.loads(process.stdout)
                message = error_json.get("error", "Runtime error")
            except Exception:
                message = process.stderr or "Runtime error"

            raise RuntimeExecutionError(message)

        try:
            result_json = json.loads(process.stdout)
            return result_json["result"]
        except Exception:
            raise RuntimeExecutionError("Invalid output format")

    # -------------------------
    # Cleanup Phase
    # -------------------------

    def cleanup(self):

        if self.container_id:
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.container_id = None

        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
            self.host_temp_dir = None
