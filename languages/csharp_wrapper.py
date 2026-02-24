CSHARP_WRAPPER_TEMPLATE = r"""
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Reflection;
using System.Linq;

// ==============================
// Built-in Data Structures
// ==============================

public class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;

    public TreeNode(int val = 0, TreeNode left = null, TreeNode right = null) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}

public class ListNode {
    public int val;
    public ListNode next;

    public ListNode(int val = 0, ListNode next = null) {
        this.val = val;
        this.next = next;
    }
}

public class Node {
    public int val;
    public IList<Node> neighbors;

    public Node() {
        val = 0;
        neighbors = new List<Node>();
    }

    public Node(int _val) {
        val = _val;
        neighbors = new List<Node>();
    }
}

// ==============================
// Helper Builders
// ==============================

public static class Builders {

    public static TreeNode BuildTree(List<int?> values) {
        if (values == null || values.Count == 0)
            return null;

        var nodes = values
            .Select(v => v == null ? null : new TreeNode(v.Value))
            .ToList();

        Queue<TreeNode> queue = new Queue<TreeNode>();
        TreeNode root = nodes[0];
        queue.Enqueue(root);

        int i = 1;
        while (queue.Count > 0 && i < nodes.Count) {
            var current = queue.Dequeue();
            if (current != null) {
                current.left = nodes[i++];
                if (i < nodes.Count)
                    current.right = nodes[i++];
                queue.Enqueue(current.left);
                queue.Enqueue(current.right);
            }
        }

        return root;
    }

    public static List<int?> TreeToList(TreeNode root) {
        if (root == null)
            return new List<int?>();

        List<int?> result = new List<int?>();
        Queue<TreeNode> queue = new Queue<TreeNode>();
        queue.Enqueue(root);

        while (queue.Count > 0) {
            var node = queue.Dequeue();
            if (node != null) {
                result.Add(node.val);
                queue.Enqueue(node.left);
                queue.Enqueue(node.right);
            } else {
                result.Add(null);
            }
        }

        while (result.Count > 0 && result.Last() == null)
            result.RemoveAt(result.Count - 1);

        return result;
    }

    public static ListNode BuildLinkedList(List<int> values, int pos) {
        if (values == null || values.Count == 0)
            return null;

        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        List<ListNode> nodes = new List<ListNode>();

        foreach (var val in values) {
            curr.next = new ListNode(val);
            curr = curr.next;
            nodes.Add(curr);
        }

        if (pos != -1 && pos < nodes.Count)
            curr.next = nodes[pos];

        return dummy.next;
    }

    public static List<int> LinkedListToList(ListNode head) {
        List<int> result = new List<int>();
        HashSet<ListNode> visited = new HashSet<ListNode>();

        while (head != null && !visited.Contains(head)) {
            visited.Add(head);
            result.Add(head.val);
            head = head.next;
        }

        return result;
    }

    public static Node BuildGraph(List<List<int>> adjList) {
        if (adjList == null || adjList.Count == 0)
            return null;

        Dictionary<int, Node> nodes = new Dictionary<int, Node>();

        for (int i = 0; i < adjList.Count; i++)
            nodes[i + 1] = new Node(i + 1);

        for (int i = 0; i < adjList.Count; i++) {
            foreach (var neighbor in adjList[i]) {
                nodes[i + 1].neighbors.Add(nodes[neighbor]);
            }
        }

        return nodes[1];
    }

    public static List<List<int>> GraphToAdjList(Node node) {
        if (node == null)
            return new List<List<int>>();

        List<Node> nodes = new List<Node>();
        Queue<Node> queue = new Queue<Node>();
        HashSet<Node> visited = new HashSet<Node>();

        queue.Enqueue(node);

        while (queue.Count > 0) {
            var curr = queue.Dequeue();
            if (visited.Contains(curr))
                continue;

            visited.Add(curr);
            nodes.Add(curr);

            foreach (var neighbor in curr.neighbors)
                if (!visited.Contains(neighbor))
                    queue.Enqueue(neighbor);
        }

        nodes = nodes.OrderBy(n => n.val).ToList();

        int maxVal = nodes.Max(n => n.val);
        List<List<int>> result = new List<List<int>>();
        for (int i = 0; i < maxVal; i++)
            result.Add(new List<int>());

        foreach (var curr in nodes)
            foreach (var neighbor in curr.neighbors)
                result[curr.val - 1].Add(neighbor.val);

        return result;
    }
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Execution Engine
// ==============================

public class Program {

    static object AutoConvertOutput(object result) {

        if (result is TreeNode tree)
            return Builders.TreeToList(tree);

        if (result is ListNode listNode)
            return Builders.LinkedListToList(listNode);

        if (result is Node graphNode)
            return Builders.GraphToAdjList(graphNode);

        return result;
    }

    static object ConvertValue(JsonElement element, Type targetType, Dictionary<string, JsonElement> fullInput) {

        if (targetType == typeof(int))
            return element.GetInt32();

        if (targetType == typeof(long))
            return element.GetInt64();

        if (targetType == typeof(double))
            return element.GetDouble();

        if (targetType == typeof(bool))
            return element.GetBoolean();

        if (targetType == typeof(string))
            return element.GetString();

        if (targetType == typeof(int[]))
            return element.EnumerateArray().Select(x => x.GetInt32()).ToArray();

        if (targetType == typeof(int[][]))
            return element.EnumerateArray()
                .Select(row => row.EnumerateArray().Select(x => x.GetInt32()).ToArray())
                .ToArray();
        
        if (targetType == typeof(char[][]))
            return element.EnumerateArray()
                .Select(row => row.EnumerateArray()
                .Select(x => x.GetString()[0])
                .ToArray())
                .ToArray();

        if (targetType == typeof(TreeNode))
            return Builders.BuildTree(
                element.EnumerateArray()
                .Select(x => x.ValueKind == JsonValueKind.Null ? (int?)null : x.GetInt32())
                .ToList()
            );

        if (targetType == typeof(ListNode)) {
            int pos = -1;
            if (fullInput.ContainsKey("pos"))
                pos = fullInput["pos"].GetInt32();

            return Builders.BuildLinkedList(
                element.EnumerateArray().Select(x => x.GetInt32()).ToList(),
                pos
            );
        }

        if (targetType == typeof(Node))
            return Builders.BuildGraph(
                element.EnumerateArray()
                .Select(row => row.EnumerateArray().Select(x => x.GetInt32()).ToList())
                .ToList()
            );

        return null;
    }

    public static void Main(string[] args) {

        try {

            string inputJson = Console.In.ReadToEnd();
            var payload = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(inputJson);

            string functionName = payload["function_name"].GetString();
            var input = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
                payload["input"].GetRawText()
            );

            Type solutionType = Type.GetType("Solution");
            object instance = Activator.CreateInstance(solutionType);

            var method = solutionType.GetMethod(functionName);
            var parameters = method.GetParameters();

            object[] argsConverted = new object[parameters.Length];
            var values = input.Values.ToList();

            for (int i = 0; i < parameters.Length; i++) {
                argsConverted[i] = ConvertValue(
                    values[i],
                    parameters[i].ParameterType,
                    input
                );
            }

            var result = method.Invoke(instance, argsConverted);
            var output = AutoConvertOutput(result);

            var response = new Dictionary<string, object> {
                { "result", output }
            };

            Console.WriteLine(JsonSerializer.Serialize(response));
        }
        catch (Exception ex) {

            var error = new Dictionary<string, object> {
                { "error", ex.InnerException?.Message ?? ex.Message }
            };

            Console.WriteLine(JsonSerializer.Serialize(error));
            Environment.Exit(1);
        }
    }
}
"""