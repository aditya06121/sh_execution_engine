import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Tuple

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

from .go_wrapper import GO_WRAPPER_TEMPLATE


class GoExecutor(BaseExecutor):

    IMAGE_NAME = "go-sandbox:latest"

    def __init__(self, code: str, function_name: str):
        super().__init__(code, function_name)
        self.container_id = None
        self.temp_dir = None
        self.host_temp_dir = None
        self.file_path = None

    # -------------------------
    # Compile Phase
    # -------------------------

    def compile(self):

        container_sandbox_root, host_sandbox_root = get_sandbox_roots()

        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)
        self.host_temp_dir = build_host_temp_dir(host_sandbox_root, self.temp_dir)
        self.file_path = os.path.join(self.temp_dir, "main.go")

        wrapped_code = self._generate_wrapper()

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
            raise RuntimeExecutionError("Failed to start execution container")

        compile_cmd = [
            "docker", "exec",
            self.container_id,
            "go",
            "build",
            "-buildvcs=false",
            "-trimpath",
            "-o",
            "main",
            "main.go"
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
            "./main"
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

    # -------------------------
    # Wrapper Generation
    # -------------------------

    def _generate_wrapper(self) -> str:
        signature = self._parse_signature()
        params = self._parse_params(signature["params"])
        returns = self._parse_returns(signature["returns"])

        param_lines = []
        for param_name, param_type in params:
            if self._is_listnode_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f"    pos_{param_name} := -1",
                            f'    if rawPos_{param_name}, ok := input["pos"]; ok {{',
                            f'        if err := json.Unmarshal(rawPos_{param_name}, &pos_{param_name}); err != nil {{',
                            f'            return nil, fmt.Errorf("invalid parameter pos: %w", err)',
                            "        }",
                            "    }",
                            f'    {param_name} := buildLinkedList({param_name}_arr, pos_{param_name})',
                            "",
                        ]
                    )
                else:
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f"    pos_{param_name} := -1",
                            f'    if rawPos_{param_name}, ok := input["pos"]; ok {{',
                            f'        if err := json.Unmarshal(rawPos_{param_name}, &pos_{param_name}); err != nil {{',
                            f'            return nil, fmt.Errorf("invalid parameter pos: %w", err)',
                            "        }",
                            "    }",
                            f'    tmp_{param_name} := buildLinkedList({param_name}_arr, pos_{param_name})',
                            f"    var {param_name} ListNode",
                            f"    if tmp_{param_name} != nil {{",
                            f"        {param_name} = *tmp_{param_name}",
                            "    }",
                            "",
                        ]
                    )
            elif self._is_treenode_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []interface{{}}',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    {param_name} := buildTree({param_name}_arr)',
                            "",
                        ]
                    )
                else:
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_arr []interface{{}}',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_arr); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    tmp_{param_name} := buildTree({param_name}_arr)',
                            f"    var {param_name} TreeNode",
                            f"    if tmp_{param_name} != nil {{",
                            f"        {param_name} = *tmp_{param_name}",
                            "    }",
                            "",
                        ]
                    )
            elif self._is_graph_node_type(param_type):
                if self._is_pointer_type(param_type):
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_adj [][]int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_adj); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    {param_name} := buildGraph({param_name}_adj)',
                            "",
                        ]
                    )
                else:
                    param_lines.extend(
                        [
                            f'    raw_{param_name}, ok := input["{param_name}"]',
                            f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                            f'    var {param_name}_adj [][]int',
                            f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}_adj); err != nil {{',
                            f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                            "    }",
                            f'    tmp_{param_name} := buildGraph({param_name}_adj)',
                            f"    var {param_name} Node",
                            f"    if tmp_{param_name} != nil {{",
                            f"        {param_name} = *tmp_{param_name}",
                            "    }",
                            "",
                        ]
                    )
            else:
                param_lines.extend(
                    [
                        f'    raw_{param_name}, ok := input["{param_name}"]',
                        f'    if !ok {{ return nil, fmt.Errorf("missing parameter: {param_name}") }}',
                        f'    var {param_name} {param_type}',
                        f'    if err := json.Unmarshal(raw_{param_name}, &{param_name}); err != nil {{',
                        f'        return nil, fmt.Errorf("invalid parameter {param_name}: %w", err)',
                        "    }",
                        "",
                    ]
                )

        arg_list = ", ".join([name for name, _ in params])
        invoker_setup = ""
        invoke_expr = ""

        if signature["receiver_type"]:
            receiver_type = signature["receiver_type"]
            if receiver_type.startswith("*"):
                setup_type = receiver_type.lstrip("*")
                invoker_setup = f"    solver := &{setup_type}{{}}"
            else:
                invoker_setup = f"    solver := {receiver_type}{{}}"
            invoke_expr = f"solver.{self.function_name}({arg_list})"
        else:
            invoke_expr = f"{self.function_name}({arg_list})"

        call_block = self._build_call_block(invoke_expr, returns)

        wrapped = GO_WRAPPER_TEMPLATE \
            .replace("{source_code}", self.code) \
            .replace("__FUNCTION_NAME_PLACEHOLDER__", self.function_name) \
            .replace("__PARAM_BINDINGS_PLACEHOLDER__", "\n".join(param_lines).rstrip()) \
            .replace("__INVOKER_SETUP_PLACEHOLDER__", invoker_setup) \
            .replace("__CALL_PLACEHOLDER__", call_block)

        return wrapped

    def _build_call_block(self, invoke_expr: str, returns: List[str]) -> str:
        if len(returns) == 0:
            return (
                f"    {invoke_expr}\n"
                "    return nil, nil"
            )

        if len(returns) == 1:
            if returns[0] == "error":
                return (
                    f"    err := {invoke_expr}\n"
                    "    if err != nil { return nil, err }\n"
                    "    return nil, nil"
                )
            return (
                f"    result := {invoke_expr}\n"
                "    return autoConvertOutput(result), nil"
            )

        if len(returns) == 2 and returns[1] == "error":
            return (
                f"    result, err := {invoke_expr}\n"
                "    if err != nil { return nil, err }\n"
                "    return autoConvertOutput(result), nil"
            )

        raise CompileError(
            "Unsupported Go return signature. Use no return, single return, error, or (T, error)."
        )

    def _parse_signature(self) -> dict:
        method_pattern = re.compile(
            rf"func\s*\(\s*(?P<receiver>[^)]*?)\s*\)\s*{re.escape(self.function_name)}\s*\((?P<params>.*?)\)\s*(?P<returns>\([^)]*\)|[^\s{{]+)?\s*\{{",
            re.DOTALL,
        )
        function_pattern = re.compile(
            rf"func\s+{re.escape(self.function_name)}\s*\((?P<params>.*?)\)\s*(?P<returns>\([^)]*\)|[^\s{{]+)?\s*\{{",
            re.DOTALL,
        )

        method_match = method_pattern.search(self.code)
        if method_match:
            receiver_type = self._extract_receiver_type(method_match.group("receiver"))
            return {
                "params": (method_match.group("params") or "").strip(),
                "returns": (method_match.group("returns") or "").strip(),
                "receiver_type": receiver_type,
            }

        function_match = function_pattern.search(self.code)
        if function_match:
            return {
                "params": (function_match.group("params") or "").strip(),
                "returns": (function_match.group("returns") or "").strip(),
                "receiver_type": None,
            }

        raise CompileError(
            f"Could not parse Go function '{self.function_name}' signature"
        )

    def _extract_receiver_type(self, receiver_decl: str) -> str:
        receiver_decl = receiver_decl.strip()
        if not receiver_decl:
            raise CompileError("Invalid Go method receiver")

        parts = receiver_decl.split()
        if len(parts) == 1:
            return parts[0]
        return parts[-1]

    def _parse_params(self, params_str: str) -> List[Tuple[str, str]]:
        if not params_str.strip():
            return []

        params: List[Tuple[str, str]] = []
        segments = self._split_top_level(params_str)

        for segment in segments:
            piece = segment.strip()
            if not piece:
                continue

            if " " not in piece:
                raise CompileError(f"Unsupported Go parameter: '{piece}'")

            names_part, type_part = piece.rsplit(" ", 1)
            param_names = [x.strip() for x in names_part.split(",") if x.strip()]

            if not param_names or not type_part.strip():
                raise CompileError(f"Invalid Go parameter: '{piece}'")

            for param_name in param_names:
                if param_name == "_":
                    raise CompileError("Blank identifier '_' is not supported as input parameter")
                params.append((param_name, type_part.strip()))

        return params

    def _parse_returns(self, returns_str: str) -> List[str]:
        raw = returns_str.strip()
        if not raw:
            return []

        if raw.startswith("(") and raw.endswith(")"):
            inner = raw[1:-1].strip()
            if not inner:
                return []

            parts = self._split_top_level(inner)
            return [self._extract_return_type(x.strip()) for x in parts if x.strip()]

        return [self._extract_return_type(raw)]

    def _extract_return_type(self, token: str) -> str:
        token = token.strip()
        if not token:
            raise CompileError("Invalid Go return type")

        if " " in token:
            return token.rsplit(" ", 1)[-1].strip()
        return token

    def _normalize_type(self, type_name: str) -> str:
        return "".join(type_name.split())

    def _is_listnode_type(self, type_name: str) -> bool:
        normalized = self._normalize_type(type_name)
        return normalized in {"*ListNode", "ListNode"}

    def _is_treenode_type(self, type_name: str) -> bool:
        normalized = self._normalize_type(type_name)
        return normalized in {"*TreeNode", "TreeNode"}

    def _is_graph_node_type(self, type_name: str) -> bool:
        normalized = self._normalize_type(type_name)
        return normalized in {"*Node", "Node"}

    def _is_pointer_type(self, type_name: str) -> bool:
        return self._normalize_type(type_name).startswith("*")

    def _split_top_level(self, value: str) -> List[str]:
        parts = []
        current = []
        depth_paren = 0
        depth_bracket = 0
        depth_brace = 0

        for ch in value:
            if ch == "," and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
                parts.append("".join(current).strip())
                current = []
                continue

            if ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren -= 1
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket -= 1
            elif ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace -= 1

            current.append(ch)

        tail = "".join(current).strip()
        if tail:
            parts.append(tail)

        return parts
