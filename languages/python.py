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


class PythonExecutor(BaseExecutor):
#TODO: write custom wrapper
    IMAGE_NAME = "python:3.11-slim"

    PYTHON_WRAPPER_TEMPLATE = """
import sys
import json
import traceback
import inspect
from collections import deque

# ==============================
# Built-in Data Structures
# ==============================

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


# ==============================
# Helper Builders
# ==============================

def build_tree(values):
    if not values:
        return None

    nodes = [TreeNode(val) if val is not None else None for val in values]
    kids = deque(nodes[1:])

    for node in nodes:
        if node:
            if kids:
                node.left = kids.popleft()
            if kids:
                node.right = kids.popleft()

    return nodes[0]


def tree_to_list(root):
    if not root:
        return []

    result = []
    queue = deque([root])

    while queue:
        node = queue.popleft()
        if node:
            result.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            result.append(None)

    while result and result[-1] is None:
        result.pop()

    return result


def build_linked_list(values):
    if not values:
        return None

    dummy = ListNode(0)
    curr = dummy

    for val in values:
        curr.next = ListNode(val)
        curr = curr.next

    return dummy.next


def linked_list_to_list(head):
    result = []

    while head:
        result.append(head.val)
        head = head.next

    return result


# ==============================
# Graph Support
# ==============================

def build_graph(adjList):
    if not adjList:
        return None

    nodes = {i + 1: Node(i + 1) for i in range(len(adjList))}

    for i, neighbors in enumerate(adjList):
        for neighbor in neighbors:
            nodes[i + 1].neighbors.append(nodes[neighbor])

    return nodes[1]


def graph_to_adjlist(node):
    if not node:
        return []

    visited = set()
    queue = deque([node])
    nodes = []

    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue

        visited.add(curr)
        nodes.append(curr)

        for neighbor in curr.neighbors:
            if neighbor not in visited:
                queue.append(neighbor)

    nodes.sort(key=lambda x: x.val)

    max_val = max(n.val for n in nodes)
    result = [[] for _ in range(max_val)]

    for curr in nodes:
        for neighbor in curr.neighbors:
            result[curr.val - 1].append(neighbor.val)

    return result


# ==============================
# User Code
# ==============================

{source_code}


# ==============================
# Execution Logic
# ==============================

def auto_convert_inputs(test_input):
    converted = {}

    for key, value in test_input.items():

        if isinstance(value, list) and key.lower().startswith("root"):
            converted[key] = build_tree(value)

        elif isinstance(value, list) and key.lower().startswith("head"):
            converted[key] = build_linked_list(value)

        elif isinstance(value, list) and key.lower().startswith("adj"):
            converted[key] = build_graph(value)

        else:
            converted[key] = value

    return converted


def auto_convert_output(result):

    if isinstance(result, TreeNode):
        return tree_to_list(result)

    if isinstance(result, ListNode):
        return linked_list_to_list(result)

    if isinstance(result, Node):
        return graph_to_adjlist(result)

    return result


def call_function(func, converted_input):

    try:
        sig = inspect.signature(func)
        param_count = len(sig.parameters)

        if param_count == len(converted_input):
            return func(*converted_input.values())

        return func(**converted_input)

    except TypeError:
        return func(**converted_input)


def execute_function(function_name, test_input):

    converted_input = auto_convert_inputs(test_input)

    # Top-level function
    if function_name in globals() and callable(globals()[function_name]):
        func = globals()[function_name]
        result = call_function(func, converted_input)
        return auto_convert_output(result)

    # Class-based Solution
    if "Solution" in globals():
        solution_instance = globals()["Solution"]()

        if hasattr(solution_instance, function_name):
            method = getattr(solution_instance, function_name)
            result = call_function(method, converted_input)
            return auto_convert_output(result)

    raise Exception(f"Function '{function_name}' not found")


def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)

        function_name = payload["function_name"]
        test_input = payload["input"]

        result = execute_function(function_name, test_input)

        print(json.dumps({"result": result}))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "trace": traceback.format_exc()
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()

"""



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

        # 1️⃣ Syntax validation

        #  for linux replace the sandbox logic with this 

        try:
            compile(self.code, "<string>", "exec")
        except SyntaxError as e:
            raise CompileError(str(e))

        container_sandbox_root = "/sandbox"
        host_sandbox_root = os.environ.get("HOST_SANDBOX_ROOT")

        if not host_sandbox_root:
            raise RuntimeExecutionError("HOST_SANDBOX_ROOT not set")

        # 2️⃣ Create temp directory inside container sandbox
        self.temp_dir = tempfile.mkdtemp(dir=container_sandbox_root)

        # Extract folder name only
        folder_name = os.path.basename(self.temp_dir)

        # Construct real host path manually
        self.host_temp_dir = os.path.join(host_sandbox_root, folder_name)

        # 3️⃣ Write wrapped code
        self.file_path = os.path.join(self.temp_dir, "main.py")

        wrapped_code = self.PYTHON_WRAPPER_TEMPLATE.replace(
    "{source_code}", self.code
)


        with open(self.file_path, "w") as f:
            f.write(wrapped_code)

        # 4️⃣ Start execution container (IMPORTANT: use host path)
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
            "python3", "main.py"
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

        # Output limit enforcement
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
