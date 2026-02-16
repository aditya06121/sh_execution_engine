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