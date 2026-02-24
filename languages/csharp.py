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
from execution.sandbox_paths import (
    build_host_temp_dir,
    get_sandbox_roots,
)

from config.limits import (
    EXECUTION_TIMEOUT_SECONDS,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_SECONDS,
)

from .csharp_wrapper import CSHARP_WRAPPER_TEMPLATE


class CSharpExecutor(BaseExecutor):

    IMAGE_NAME = "csharp-sandbox:latest"

    # 🔒 Safe limits for .NET SDK
    SAFE_PIDS_LIMIT = "512"
    SAFE_NOFILE_LIMIT = "65535"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.project_path = None

    # -------------------------
    # Compile Phase
    # -------------------------

    def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)

        self.project_path = os.path.join(self.temp_dir, "SandboxApp")
        os.makedirs(self.project_path, exist_ok=True)

        program_path = os.path.join(self.project_path, "Program.cs")

        wrapped_code = CSHARP_WRAPPER_TEMPLATE.replace(
            "{source_code}", self.code
        )

        with open(program_path, "w") as f:
            f.write(wrapped_code)

        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
  </PropertyGroup>
</Project>
"""
        with open(os.path.join(self.project_path, "SandboxApp.csproj"), "w") as f:
            f.write(csproj_content)

        run_cmd = [
            "docker", "run",
            "-d",
            "--rm",

            "--memory", DOCKER_MEMORY_LIMIT,
            "--memory-swap", DOCKER_MEMORY_SWAP,
            "--cpus", DOCKER_CPU_LIMIT,
            "--pids-limit", self.SAFE_PIDS_LIMIT,
            "--ulimit", f"nofile={self.SAFE_NOFILE_LIMIT}:{self.SAFE_NOFILE_LIMIT}",

            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",

            "-v", f"{self.host_temp_dir}:/app",
            "-w", "/app/SandboxApp",

            self.IMAGE_NAME,
            "sleep", str(CONTAINER_SLEEP_SECONDS)
        ]

        try:
            proc = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.container_id = proc.stdout.strip()
        except subprocess.CalledProcessError:
            raise RuntimeExecutionError("Failed to start execution container")

        compile_cmd = [
            "docker", "exec",
            self.container_id,
            "dotnet",
            "build",
            "--configuration", "Release",
            "--nologo"
        ]

        try:
            compile_proc = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            raise CompileError("Compilation timed out")

        if compile_proc.returncode != 0:
            raise CompileError(
                compile_proc.stderr.strip() or "Compilation failed"
            )

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
            "dotnet",
            "/app/SandboxApp/bin/Release/net8.0/SandboxApp.dll"
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