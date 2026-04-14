import asyncio
import json
import os
import re
import shutil
import tempfile

from config.limits import (
    COMPILATION_TIMEOUT_SECONDS,
    CONTAINER_SLEEP_SECONDS,
    DOCKER_CPU_LIMIT,
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_NOFILE_LIMIT,
    DOCKER_PIDS_LIMIT,
    EXECUTION_TIMEOUT_SECONDS,
    MAX_STDOUT_BYTES,
)
from execution.base import BaseExecutor
from execution.exceptions import CompileError, RuntimeExecutionError
from execution.sandbox_paths import build_host_temp_dir, get_sandbox_roots

from .rust_wrapper import RUST_WRAPPER_TEMPLATE

PIPE = asyncio.subprocess.PIPE
DEVNULL = asyncio.subprocess.DEVNULL


class RustExecutor(BaseExecutor):

    IMAGE_NAME = "rust-sandbox:latest"
    VENDORED_SOURCE_DIR = "/opt/cache/runner/vendor"
    SHARED_TARGET_DIR = "/opt/cache/runner/target"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None

    # ==========================================================
    # Compile Phase
    # ==========================================================

    async def compile(self):

        container_root, host_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_root)
        self.host_temp_dir = build_host_temp_dir(host_root, self.temp_dir)

        wrapped_code = self._generate_wrapper()

        if "__PLACEHOLDER__" in wrapped_code or "__FUNCTION_" in wrapped_code:
            raise CompileError("Wrapper placeholder replacement failed")

        src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(src_dir, "main.rs"), "w") as f:
            f.write(wrapped_code)

        cargo_toml = """
[package]
name = "runner"
version = "0.1.0"
edition = "2021"

[dependencies]
serde_json = "1"
"""
        with open(os.path.join(self.temp_dir, "Cargo.toml"), "w") as f:
            f.write(cargo_toml)

        cargo_config_dir = os.path.join(self.temp_dir, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        cargo_config = f"""[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "{self.VENDORED_SOURCE_DIR}"
"""
        with open(os.path.join(cargo_config_dir, "config.toml"), "w") as f:
            f.write(cargo_config)

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
            raise RuntimeExecutionError("Failed to start Rust container")
        self.container_id = stdout.decode().strip()

        compile_cmd = [
            "docker", "exec", self.container_id,
            "cargo", "build", "--release", "--offline",
            "--target-dir", self.SHARED_TARGET_DIR,
        ]

        proc = await asyncio.create_subprocess_exec(*compile_cmd, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMPILATION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise CompileError("Compilation timed out")

        if proc.returncode != 0:
            raise CompileError(stderr.decode().strip()[:1000])

    # ==========================================================
    # Run Phase
    # ==========================================================

    async def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps(test_input, separators=(",", ":")).encode()

        exec_cmd = [
            "docker", "exec", "-i", self.container_id,
            f"{self.SHARED_TARGET_DIR}/release/runner",
        ]

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

        _, params = self._parse_signature()

        param_deserialization = []
        function_arguments = []

        for param_type, param_name in params:
            normalized_type = self._normalize_type(param_type)
            binding_code, invocation_arg = self._build_param_binding(normalized_type, param_name)
            param_deserialization.extend(binding_code)
            function_arguments.append(invocation_arg)

        wrapper = (
            RUST_WRAPPER_TEMPLATE
            .replace("__FUNCTION_SIGNATURE_PLACEHOLDER__", "")
            .replace("__PARAMETER_DESERIALIZATION_PLACEHOLDER__", "\n    ".join(param_deserialization))
            .replace("__FUNCTION_NAME_PLACEHOLDER__", self.function_name)
            .replace("__FUNCTION_ARGUMENT_LIST_PLACEHOLDER__", ", ".join(function_arguments))
            .replace("__RETURN_SERIALIZATION_PLACEHOLDER__", "json!(result)")
            .replace("__USER_CODE_PLACEHOLDER__", self.code)
        )

        return wrapper

    # ==========================================================
    # Signature Parser
    # ==========================================================

    def _parse_signature(self):

        pattern = rf'fn\s+{re.escape(self.function_name)}\s*\((.*?)\)\s*(?:->\s*([^\{{]+))?\s*\{{'
        match = re.search(pattern, self.code, re.DOTALL)

        if not match:
            raise CompileError("Could not parse Rust function signature")

        params_str = match.group(1).strip()
        return_type = (match.group(2) or "()").strip()

        params = []

        if params_str:
            raw_params = [p.strip() for p in self._split_top_level(params_str)]

            for p in raw_params:
                if ":" not in p:
                    raise CompileError(f"Invalid Rust parameter syntax: {p}")
                name, typ = p.split(":", 1)
                clean_name = name.strip().replace("mut ", "")
                params.append((typ.strip(), clean_name))

        return return_type, params

    def _split_top_level(self, content: str):
        segments = []
        current = []
        angle_depth = 0
        paren_depth = 0
        bracket_depth = 0

        for ch in content:
            if ch == "<":
                angle_depth += 1
            elif ch == ">":
                angle_depth = max(0, angle_depth - 1)
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)

            if ch == "," and angle_depth == 0 and paren_depth == 0 and bracket_depth == 0:
                piece = "".join(current).strip()
                if piece:
                    segments.append(piece)
                current = []
                continue

            current.append(ch)

        tail = "".join(current).strip()
        if tail:
            segments.append(tail)
        return segments

    def _normalize_type(self, type_name: str) -> str:
        return " ".join(type_name.strip().split())

    def _build_param_binding(self, type_name: str, param_name: str):
        if type_name.startswith("&mut "):
            owned_type = self._resolve_owned_reference_target(type_name[5:].strip())
            lines = [
                f'let mut {param_name}_owned: {owned_type} = serde_json::from_value(j["{param_name}"].clone()).unwrap();'
            ]
            return lines, f"&mut {param_name}_owned"

        if type_name.startswith("&"):
            owned_type = self._resolve_owned_reference_target(type_name[1:].strip())
            lines = [
                f'let {param_name}_owned: {owned_type} = serde_json::from_value(j["{param_name}"].clone()).unwrap();'
            ]
            return lines, f"&{param_name}_owned"

        lines = [
            f'let {param_name}: {type_name} = serde_json::from_value(j["{param_name}"].clone()).unwrap();'
        ]
        return lines, param_name

    def _resolve_owned_reference_target(self, borrowed_type: str) -> str:
        inner = borrowed_type.strip()
        if inner == "str":
            return "String"
        if inner.startswith("[") and inner.endswith("]"):
            return f"Vec<{inner[1:-1].strip()}>"
        return inner
