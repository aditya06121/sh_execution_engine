JAVA_WRAPPER_TEMPLATE = r"""
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;

// ==============================
// Built-in Data Structures
// ==============================

class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;
    TreeNode(int val) { this.val = val; }
}

class ListNode {
    public int val;
    public ListNode next;
    ListNode(int val) { this.val = val; }
}

class Node {
    public int val;
    public List<Node> neighbors;
    Node(int val) {
        this.val = val;
        this.neighbors = new ArrayList<>();
    }
}

// ==============================
// Helper Builders
// ==============================

class Builders {

    public static TreeNode buildTree(List<Integer> values) {
        if (values == null || values.isEmpty()) return null;

        List<TreeNode> nodes = new ArrayList<>();
        for (Integer val : values)
            nodes.add(val == null ? null : new TreeNode(val));

        Queue<TreeNode> queue = new LinkedList<>();
        TreeNode root = nodes.get(0);
        queue.offer(root);

        int i = 1;
        while (!queue.isEmpty() && i < nodes.size()) {
            TreeNode current = queue.poll();
            if (current != null) {
                current.left = nodes.get(i++);
                if (i < nodes.size())
                    current.right = nodes.get(i++);
                queue.offer(current.left);
                queue.offer(current.right);
            }
        }

        return root;
    }

    public static List<Integer> treeToList(TreeNode root) {
        if (root == null) return new ArrayList<>();

        List<Integer> result = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        queue.offer(root);

        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            if (node != null) {
                result.add(node.val);
                queue.offer(node.left);
                queue.offer(node.right);
            } else {
                result.add(null);
            }
        }

        while (!result.isEmpty() && result.get(result.size() - 1) == null)
            result.remove(result.size() - 1);

        return result;
    }

    public static ListNode buildLinkedList(List<Integer> values, int pos) {
        if (values == null || values.isEmpty()) return null;

        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        List<ListNode> nodes = new ArrayList<>();

        for (Integer val : values) {
            curr.next = new ListNode(val);
            curr = curr.next;
            nodes.add(curr);
        }

        if (pos != -1 && pos < nodes.size())
            curr.next = nodes.get(pos);

        return dummy.next;
    }

    public static List<Integer> linkedListToList(ListNode head) {
        List<Integer> result = new ArrayList<>();
        Set<ListNode> visited = new HashSet<>();

        while (head != null && !visited.contains(head)) {
            visited.add(head);
            result.add(head.val);
            head = head.next;
        }

        return result;
    }

    public static Node buildGraph(List<List<Integer>> adjList) {
        if (adjList == null || adjList.isEmpty()) return null;

        Map<Integer, Node> nodes = new HashMap<>();
        for (int i = 0; i < adjList.size(); i++)
            nodes.put(i + 1, new Node(i + 1));

        for (int i = 0; i < adjList.size(); i++)
            for (Integer neighbor : adjList.get(i))
                nodes.get(i + 1).neighbors.add(nodes.get(neighbor));

        return nodes.get(1);
    }

    public static List<List<Integer>> graphToAdjList(Node node) {
        if (node == null) return new ArrayList<>();

        List<Node> nodes = new ArrayList<>();
        Queue<Node> queue = new LinkedList<>();
        Set<Node> visited = new HashSet<>();

        queue.offer(node);

        while (!queue.isEmpty()) {
            Node curr = queue.poll();
            if (visited.contains(curr)) continue;

            visited.add(curr);
            nodes.add(curr);

            for (Node neighbor : curr.neighbors)
                if (!visited.contains(neighbor))
                    queue.offer(neighbor);
        }

        nodes.sort(Comparator.comparingInt(n -> n.val));

        int maxVal = nodes.stream().mapToInt(n -> n.val).max().orElse(0);
        List<List<Integer>> result = new ArrayList<>();
        for (int i = 0; i < maxVal; i++)
            result.add(new ArrayList<>());

        for (Node curr : nodes)
            for (Node neighbor : curr.neighbors)
                result.get(curr.val - 1).add(neighbor.val);

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

public class Main {

    static ObjectMapper mapper = new ObjectMapper();

    public static Object autoConvertOutput(Object result) {

        if (result instanceof TreeNode)
            return Builders.treeToList((TreeNode) result);

        if (result instanceof ListNode)
            return Builders.linkedListToList((ListNode) result);

        if (result instanceof Node)
            return Builders.graphToAdjList((Node) result);

        return result;
    }

    public static Object convertValue(Object value, Class<?> targetType, Map<String,Object> fullInput) {

        if (value == null)
            return null;

        if (targetType == int.class || targetType == Integer.class)
            return ((Number) value).intValue();

        if (targetType == long.class || targetType == Long.class)
            return ((Number) value).longValue();

        if (targetType == double.class || targetType == Double.class)
            return ((Number) value).doubleValue();

        if (targetType == boolean.class || targetType == Boolean.class)
            return value;

        if (targetType == String.class)
            return value.toString();

        if (targetType == int[].class) {
            List<?> list = (List<?>) value;
            int[] arr = new int[list.size()];
            for (int i = 0; i < list.size(); i++)
                arr[i] = ((Number) list.get(i)).intValue();
            return arr;
        }

        if (targetType == int[][].class) {
            List<?> outer = (List<?>) value;
            int[][] arr = new int[outer.size()][];
            for (int i = 0; i < outer.size(); i++) {
                List<?> inner = (List<?>) outer.get(i);
                arr[i] = new int[inner.size()];
                for (int j = 0; j < inner.size(); j++)
                    arr[i][j] = ((Number) inner.get(j)).intValue();
            }
            return arr;
        }

        if (targetType == TreeNode.class)
            return Builders.buildTree((List<Integer>) value);

        if (targetType == ListNode.class) {
            int pos = -1;
            if (fullInput.containsKey("pos"))
                pos = ((Number) fullInput.get("pos")).intValue();
            return Builders.buildLinkedList((List<Integer>) value, pos);
        }

        if (targetType == Node.class)
            return Builders.buildGraph((List<List<Integer>>) value);

        return value;
    }

    public static Object executeFunction(String functionName, Map<String, Object> input) throws Exception {

        try {
            Class<?> solutionClass = Class.forName("Solution");
            Object instance = solutionClass.getDeclaredConstructor().newInstance();

            for (Method method : solutionClass.getDeclaredMethods()) {

                if (!method.getName().equals(functionName))
                    continue;

                Class<?>[] paramTypes = method.getParameterTypes();
                Object[] args = new Object[paramTypes.length];

                List<Object> values = new ArrayList<>(input.values());

                for (int i = 0; i < paramTypes.length; i++)
                    args[i] = convertValue(values.get(i), paramTypes[i], input);

                Object result = method.invoke(instance, args);
                return autoConvertOutput(result);
            }

        } catch (InvocationTargetException e) {
            throw new Exception(e.getTargetException().getMessage());
        } catch (ClassNotFoundException ignored) {}

        throw new Exception("Function '" + functionName + "' not found");
    }

    public static void main(String[] args) {

        try {

            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
            StringBuilder inputBuilder = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null)
                inputBuilder.append(line);

            Map<String, Object> payload =
                mapper.readValue(inputBuilder.toString(),
                    new TypeReference<Map<String, Object>>() {});

            String functionName = (String) payload.get("function_name");
            Map<String, Object> input =
                (Map<String, Object>) payload.get("input");

            Object result = executeFunction(functionName, input);

            Map<String, Object> response = new HashMap<>();
            response.put("result", result);

            System.out.println(mapper.writeValueAsString(response));

        } catch (Exception e) {

            try {
                Map<String, Object> error = new HashMap<>();
                error.put("error", e.getMessage());
                System.out.println(mapper.writeValueAsString(error));
            } catch (Exception ignored) {}

            System.exit(1);
        }
    }
}
"""