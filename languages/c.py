import subprocess
import tempfile
import os
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

from .c_wrapper import C_WRAPPER_TEMPLATE


class CExecutor(BaseExecutor):

    IMAGE_NAME = "cpp-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.file_path = None

    # ==========================================================
    # COMPILE PHASE
    # ==========================================================

    def compile(self):

        container_root, host_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_root)
        self.host_temp_dir = build_host_temp_dir(host_root, self.temp_dir)

        wrapped_code = self._generate_wrapper()

        self.file_path = os.path.join(self.temp_dir, "solution.c")

        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

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
            raise RuntimeExecutionError("Failed to start C container")

        compile_cmd = [
            "docker", "exec",
            self.container_id,
            "gcc",
            "solution.c",
            "-O2",
            "-std=c11",
            "-o",
            "solution"
        ]

        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise CompileError(result.stderr.strip())

    # ==========================================================
    # RUN PHASE
    # ==========================================================

    def run(self, test_input: dict):

        if not self.container_id:
            raise RuntimeExecutionError("Container not initialized")

        stdin_payload = self._build_stdin(test_input)

        exec_cmd = [
            "docker", "exec",
            "-i",
            self.container_id,
            "./solution"
        ]

        try:
            process = subprocess.run(
                exec_cmd,
                input=stdin_payload,
                text=True,
                capture_output=True,
                timeout=EXECUTION_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            raise RuntimeExecutionError("Execution timed out")

        if len(process.stdout.encode()) > MAX_STDOUT_BYTES:
            raise RuntimeExecutionError("Output limit exceeded")

        if process.returncode != 0:
            raise RuntimeExecutionError(
                process.stderr.strip() or "Runtime error"
            )

        return process.stdout.strip()

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

    # ==========================================================
    # WRAPPER GENERATOR
    # ==========================================================

    def _generate_wrapper(self):

        return_type, params = self._parse_signature()

        input_decl = []
        input_scan = []
        function_args = []
        cleanup = []
        output_print = ""

        for param_type, param_name in params:

            if param_type == "int":
                input_decl.append(f"int {param_name};")
                input_scan.append(f'scanf("%d", &{param_name});')
                function_args.append(param_name)

            elif param_type == "long long":
                input_decl.append(f"long long {param_name};")
                input_scan.append(f'scanf("%lld", &{param_name});')
                function_args.append(param_name)

            elif param_type == "double":
                input_decl.append(f"double {param_name};")
                input_scan.append(f'scanf("%lf", &{param_name});')
                function_args.append(param_name)

            elif param_type == "int*":
                size_name = param_name + "Size"

                input_decl.append(f"int {size_name};")
                input_decl.append(f"int* {param_name};")

                input_scan.append(f'scanf("%d", &{size_name});')
                input_scan.append(
                    f'{param_name} = (int*)malloc(sizeof(int) * {size_name});'
                )
                input_scan.append(
                    f'for(int i=0;i<{size_name};i++) scanf("%d",&{param_name}[i]);'
                )

                function_args.append(param_name)
                function_args.append(size_name)

                cleanup.append(f"free({param_name});")

            else:
                raise CompileError(f"Unsupported C type: {param_type}")

        # Return handling
        if return_type == "int":
            output_print = 'printf("%d", result);'
        elif return_type == "long long":
            output_print = 'printf("%lld", result);'
        elif return_type == "double":
            output_print = 'printf("%f", result);'
        else:
            raise CompileError("Unsupported return type")

        function_call = f"{return_type} result = {self.function_name}({', '.join(function_args)});"

        wrapper = C_WRAPPER_TEMPLATE \
            .replace("__FUNCTION_SIGNATURE_PLACEHOLDER__",
                     f"{return_type} {self.function_name}({', '.join([f'{t} {n}' for t,n in params])});") \
            .replace("__INPUT_DECLARATION_PLACEHOLDER__",
                     "\n    ".join(input_decl)) \
            .replace("__INPUT_SCAN_PLACEHOLDER__",
                     "\n    ".join(input_scan)) \
            .replace("__FUNCTION_CALL_PLACEHOLDER__",
                     function_call) \
            .replace("__OUTPUT_PRINT_PLACEHOLDER__",
                     output_print) \
            .replace("__CLEANUP_PLACEHOLDER__",
                     "\n    ".join(cleanup)) \
            .replace("__USER_CODE_PLACEHOLDER__",
                     self.code)

        return wrapper

    # ==========================================================
    # SIGNATURE PARSER
    # ==========================================================

    def _parse_signature(self):

        pattern = rf'([a-zA-Z_][a-zA-Z0-9_ \*]*)\s+{self.function_name}\s*\((.*?)\)'
        match = re.search(pattern, self.code)

        if not match:
            raise CompileError("Could not parse function signature")

        return_type = match.group(1).strip()
        params_str = match.group(2).strip()

        params = []

        if params_str:
            raw_params = [p.strip() for p in params_str.split(",")]
            for p in raw_params:
                parts = p.split()
                param_name = parts[-1]
                param_type = " ".join(parts[:-1])
                params.append((param_type.strip(), param_name.strip()))

        return return_type, params

    # ==========================================================
    # STDIN BUILDER
    # ==========================================================

    def _build_stdin(self, test_input: dict):

        lines = []

        for value in test_input.values():
            if isinstance(value, list):
                lines.append(str(len(value)))
                lines.append(" ".join(map(str, value)))
            else:
                lines.append(str(value))

        return "\n".join(lines)