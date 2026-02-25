import subprocess
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
    DOCKER_MEMORY_LIMIT,
    DOCKER_MEMORY_SWAP,
    DOCKER_CPU_LIMIT,
    DOCKER_PIDS_LIMIT,
    DOCKER_NOFILE_LIMIT,
    MAX_STDOUT_BYTES,
    CONTAINER_SLEEP_SECONDS,
)

from .cpp_wrapper import CPP_WRAPPER_TEMPLATE


class CppExecutor(BaseExecutor):

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

    def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(
            host_sandbox_root,
            self.temp_dir
        )

        # Generate wrapper
        wrapped_code = self._generate_wrapper()

        # Safety check
        if "__PLACEHOLDER__" in wrapped_code or "__FUNCTION_" in wrapped_code:
            raise CompileError("Wrapper placeholder replacement failed")

        self.file_path = os.path.join(self.temp_dir, "solution.cpp")

        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        # Start container
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
            raise RuntimeExecutionError("Failed to start C++ container")

        # Compile inside container
        compile_cmd = [
            "docker", "exec",
            self.container_id,
            "g++",
            "solution.cpp",
            "-O2",
            "-std=c++20",
            "-o",
            "solution"
        ]

        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise CompileError(result.stderr)

    # ==========================================================
    # Run Phase
    # ==========================================================

    def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        payload = json.dumps(test_input)

        exec_cmd = [
            "docker", "exec",
            "-i",
            self.container_id,
            "./solution"
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
            raise RuntimeExecutionError(
                process.stderr.strip() or process.stdout.strip() or "Runtime error"
            )

        try:
            return json.loads(process.stdout.strip())
        except Exception:
            raise RuntimeExecutionError("Invalid JSON output")

    # ==========================================================
    # Cleanup Phase
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

    # ==========================================================
    # Wrapper Generator
    # ==========================================================

    def _generate_wrapper(self):

        return_type, params = self._parse_signature()

        param_deserialization = []
        param_names = []

        for param_type, param_name in params:

            clean_type = param_type.replace("const", "").replace("&", "").strip()

            # ===============================
            # Primitive types
            # ===============================
            if clean_type == "int":
                param_deserialization.append(
                    f'int {param_name} = j["{param_name}"];'
                )

            elif clean_type == "long long":
                param_deserialization.append(
                    f'long long {param_name} = j["{param_name}"];'
                )

            elif clean_type == "string":
                param_deserialization.append(
                    f'string {param_name} = j["{param_name}"];'
                )

            # ===============================
            # vector<int>
            # ===============================
            elif clean_type == "vector<int>":
                param_deserialization.append(
                    f'vector<int> {param_name} = j["{param_name}"].get<vector<int>>();'
                )

            # ===============================
            # vector<vector<int>> (Graph)
            # ===============================
            elif clean_type == "vector<vector<int>>":
                param_deserialization.append(
                    f'vector<vector<int>> {param_name} = j["{param_name}"].get<vector<vector<int>>>();'
                )

            # ===============================
            # Linked List
            # ===============================
            elif clean_type == "ListNode*":
                param_deserialization.append(
                    f'vector<int> {param_name}_vec = j["{param_name}"].get<vector<int>>();'
                )
                param_deserialization.append(
                    f'ListNode* {param_name} = buildLinkedList({param_name}_vec);'
                )

            # ===============================
            # Binary Tree
            # ===============================
            elif clean_type == "TreeNode*":
                param_deserialization.append(
                    f'vector<optional<int>> {param_name}_vec;'
                )
                param_deserialization.append(
                    f'for (auto& el : j["{param_name}"]) {{'
                )
                param_deserialization.append(
                    f'    if (el.is_null()) {param_name}_vec.push_back(nullopt);'
                )
                param_deserialization.append(
                    f'    else {param_name}_vec.push_back(el.get<int>());'
                )
                param_deserialization.append(
                    f'}}'
                )
                param_deserialization.append(
                    f'TreeNode* {param_name} = buildTree({param_name}_vec);'
                )

            else:
                raise CompileError(f"Unsupported type: {clean_type}")

            param_names.append(param_name)

        # ===============================
        # RETURN SERIALIZATION
        # ===============================

        return_serialization = "output = result;"

        if return_type == "ListNode*":
            return_serialization = "output = serializeLinkedList(result);"

        elif return_type == "TreeNode*":
            return_serialization = "output = serializeTree(result);"

        wrapper = CPP_WRAPPER_TEMPLATE \
            .replace(
                "__FUNCTION_SIGNATURE_PLACEHOLDER__",
                f"{return_type} {self.function_name}({', '.join([f'{t} {n}' for t, n in params])});"
            ) \
            .replace(
                "__PARAMETER_DESERIALIZATION_PLACEHOLDER__",
                "\n        ".join(param_deserialization)
            ) \
            .replace(
                "__FUNCTION_NAME_PLACEHOLDER__",
                self.function_name
            ) \
            .replace(
                "__FUNCTION_ARGUMENT_LIST_PLACEHOLDER__",
                ", ".join(param_names)
            ) \
            .replace(
                "__RETURN_SERIALIZATION_PLACEHOLDER__",
                return_serialization
            ) \
            .replace(
                "__USER_CODE_PLACEHOLDER__",
                self.code
            )

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