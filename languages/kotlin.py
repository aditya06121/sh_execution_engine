import subprocess
import tempfile
import os
import json
import shutil

from execution.base import BaseExecutor
from execution.exceptions import CompileError, RuntimeExecutionError
from execution.sandbox_paths import (
    build_host_temp_dir,
    get_sandbox_roots,
)

from config.limits import (
    EXECUTION_TIMEOUT_SECONDS,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_SECONDS,
)

from .kotlin_wrapper import KOTLIN_WRAPPER_TEMPLATE


class KotlinExecutor(BaseExecutor):

    IMAGE_NAME = "java-sandbox:latest"

    # Explicit jars (kotlinc does NOT expand *)
    LIB_CLASSPATH = (
        "/opt/libs/jackson-core.jar:"
        "/opt/libs/jackson-databind.jar:"
        "/opt/libs/jackson-annotations.jar"
    )

    # Runtime classpath (JVM expands *)
    RUNTIME_CLASSPATH = "main.jar:/opt/libs/*"

    def __init__(self, code: str, function_name: str):
        # Normalize escaped newlines if frontend sends them
        code = code.replace("\\n", "\n")
        super().__init__(code, function_name)

        self.temp_dir = None
        self.host_temp_dir = None
        self.container_id = None

    # ==========================================================
    # COMPILE PHASE
    # ==========================================================

    def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        # 1️⃣ Create workspace
        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)

        file_path = os.path.join(self.temp_dir, "Main.kt")

        wrapped_code = KOTLIN_WRAPPER_TEMPLATE.replace(
            "{USER_CODE}", self.code
        )

        with open(file_path, "w") as f:
            f.write(wrapped_code)

        # 2️⃣ Start container
        run_cmd = [
            "docker", "run",
            "-d",
            "--rm",
            "--memory", "512m",
            "--memory-swap", "512m",
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

        # 3️⃣ Compile Kotlin
        compile_cmd = [
            "docker", "exec",
            self.container_id,
            "kotlinc",
            "Main.kt",
            "-include-runtime",
            "-cp", self.LIB_CLASSPATH,
            "-d", "main.jar",
            "-J-Xms64m",
            "-J-Xmx256m",
            "-J-XX:MaxMetaspaceSize=128m",
            "-J-XX:+UseSerialGC"
        ]

        compile_process = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True
        )

        if compile_process.returncode != 0:
            raise CompileError(
                (compile_process.stderr or compile_process.stdout).strip()[:1000]
            )

    # ==========================================================
    # RUN PHASE
    # ==========================================================

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
            "java",
            "-Xms32m",
            "-Xmx128m",
            "-XX:+UseSerialGC",
            "-XX:TieredStopAtLevel=1",
            "-cp", self.RUNTIME_CLASSPATH,
            "MainKt"
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

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        if len(stdout.encode("utf-8")) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if process.returncode != 0:
            try:
                error_json = json.loads(stdout)
                message = error_json.get("error", "Runtime error")
            except Exception:
                message = stderr or stdout or "Runtime error"

            raise RuntimeExecutionError(message[:1000])

        try:
            result_json = json.loads(stdout)
            return result_json["result"]
        except Exception:
            raise RuntimeExecutionError(
                f"Invalid output format. Raw output:\n{stdout[:500]}"
            )

    # ==========================================================
    # CLEANUP
    # ==========================================================

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
