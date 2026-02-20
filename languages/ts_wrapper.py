TS_WRAPPER_TEMPLATE = """

// Minimal Node global declarations (avoid @types/node dependency)
declare const process: any;
declare const console: any;

// ==============================
// Built-in Data Structures
// ==============================

class TreeNode {
    val: number;
    left: TreeNode | null;
    right: TreeNode | null;

    constructor(val: number = 0, left: TreeNode | null = null, right: TreeNode | null = null) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}

class ListNode {
    val: number;
    next: ListNode | null;

    constructor(val: number = 0, next: ListNode | null = null) {
        this.val = val;
        this.next = next;
    }
}

class GraphNode {
    val: number;
    neighbors: GraphNode[];

    constructor(val: number = 0, neighbors: GraphNode[] = []) {
        this.val = val;
        this.neighbors = neighbors;
    }
}

// ==============================
// Tree Helpers
// ==============================

function buildTree(values: (number | null)[]): TreeNode | null {
    if (!values || values.length === 0) return null;

    const nodes: (TreeNode | null)[] = values.map(v =>
        v === null ? null : new TreeNode(v)
    );

    let pos = 1;
    for (let i = 0; i < nodes.length && pos < nodes.length; i++) {
        if (nodes[i]) {
            if (pos < nodes.length) nodes[i]!.left = nodes[pos++];
            if (pos < nodes.length) nodes[i]!.right = nodes[pos++];
        }
    }

    return nodes[0];
}

function treeToList(root: TreeNode | null): (number | null)[] {
    if (!root) return [];

    const result: (number | null)[] = [];
    const queue: (TreeNode | null)[] = [root];

    while (queue.length) {
        const node = queue.shift()!;
        if (node) {
            result.push(node.val);
            queue.push(node.left);
            queue.push(node.right);
        } else {
            result.push(null);
        }
    }

    while (result.length && result[result.length - 1] === null)
        result.pop();

    return result;
}

// ==============================
// Linked List Helpers (Cycle Safe)
// ==============================

function buildLinkedList(values: number[]): { head: ListNode | null, nodes: ListNode[] } {
    if (!values || values.length === 0) return { head: null, nodes: [] };

    const dummy = new ListNode(0);
    let curr: ListNode = dummy;
    const nodes: ListNode[] = [];

    for (const val of values) {
        curr.next = new ListNode(val);
        curr = curr.next;
        nodes.push(curr);
    }

    return { head: dummy.next, nodes };
}

function linkedListToArray(head: ListNode | null): number[] {
    const result: number[] = [];
    const visited = new Set<ListNode>();

    while (head && !visited.has(head)) {
        visited.add(head);
        result.push(head.val);
        head = head.next;
    }

    return result;
}

// ==============================
// Graph Helpers
// ==============================

function buildGraph(adjList: number[][]): GraphNode | null {
    if (!adjList || adjList.length === 0) return null;

    const nodes: GraphNode[] = adjList.map((_, i) => new GraphNode(i + 1));

    for (let i = 0; i < adjList.length; i++) {
        for (const neighbor of adjList[i]) {
            nodes[i].neighbors.push(nodes[neighbor - 1]);
        }
    }

    return nodes[0];
}

function graphToAdjList(node: GraphNode | null): number[][] {
    if (!node) return [];

    const visited = new Set<GraphNode>();
    const queue: GraphNode[] = [node];
    const nodes: GraphNode[] = [];

    while (queue.length) {
        const curr = queue.shift()!;
        if (visited.has(curr)) continue;

        visited.add(curr);
        nodes.push(curr);

        for (const neighbor of curr.neighbors) {
            if (!visited.has(neighbor)) {
                queue.push(neighbor);
            }
        }
    }

    nodes.sort((a, b) => a.val - b.val);

    const maxVal = Math.max(...nodes.map(n => n.val));
    const result: number[][] = Array.from({ length: maxVal }, () => []);

    for (const curr of nodes) {
        for (const neighbor of curr.neighbors) {
            result[curr.val - 1].push(neighbor.val);
        }
    }

    return result;
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Auto Conversion (Cycle Support Added)
// ==============================

function autoConvertInput(input: Record<string, any>): Record<string, any> {
    const converted: Record<string, any> = {};

    for (const key in input) {
        const value = input[key];

        // Tree
        if (Array.isArray(value) && key.toLowerCase().startsWith("root")) {
            converted[key] = buildTree(value);
        }

        // Linked List with optional pos
        else if (Array.isArray(value) && key.toLowerCase().startsWith("head")) {

            const pos = typeof input.pos === "number" ? input.pos : -1;

            const { head, nodes } = buildLinkedList(value);

            if (pos !== -1 && nodes.length > 0 && pos >= 0 && pos < nodes.length) {
                nodes[nodes.length - 1].next = nodes[pos];
            }

            converted[key] = head;
        }

        // Graph
        else if (Array.isArray(value) && key.toLowerCase().startsWith("adj")) {
            converted[key] = buildGraph(value);
        }

        // Skip metadata like pos
        else if (key === "pos") {
            continue;
        }

        else {
            converted[key] = value;
        }
    }

    return converted;
}

function autoConvertOutput(result: any): any {
    if (result instanceof TreeNode) return treeToList(result);
    if (result instanceof ListNode) return linkedListToArray(result);
    if (result instanceof GraphNode) return graphToAdjList(result);
    return result;
}

// ==============================
// Execution Logic
// ==============================

function executeFunction(functionName: string, input: Record<string, any>): any {

    const convertedInput = autoConvertInput(input);

    try {
        const func = eval(functionName);
        if (typeof func === "function") {
            const result = func(...Object.values(convertedInput));
            return autoConvertOutput(result);
        }
    } catch (_) {}

    try {
        const SolutionClass = eval("Solution");
        if (typeof SolutionClass === "function") {
            const instance = new SolutionClass();
            if (typeof instance[functionName] === "function") {
                const result = instance[functionName](...Object.values(convertedInput));
                return autoConvertOutput(result);
            }
        }
    } catch (_) {}

    throw new Error("Function '" + functionName + "' not found");
}

// ==============================
// Main
// ==============================

function main() {
    const inputChunks: any[] = [];

    process.stdin.on("data", (chunk: any) => {
        inputChunks.push(chunk);
    });

    process.stdin.on("end", () => {
        try {
            const rawInput = inputChunks.join("");
            const payload = JSON.parse(rawInput);

            const functionName = payload.function_name;
            const testInput = payload.input;

            const result = executeFunction(functionName, testInput);

            console.log(JSON.stringify({ result }));
        } catch (err: any) {
            console.log(JSON.stringify({
                error: err?.message || "Runtime error"
            }));
            process.exit(1);
        }
    });
}

main();
"""