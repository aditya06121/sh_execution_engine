JAVA_WRAPPER_TEMPLATE = r"""
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import com.fasterxml.jackson.databind.*;
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

    public Node() {
        val = 0;
        neighbors = new ArrayList<>();
    }

    public Node(int _val) {
        val = _val;
        neighbors = new ArrayList<>();
    }
}

// ==============================
// User Code
// ==============================

{USER_CODE}

// ==============================
// Execution Engine
// ==============================

public class Main {

    static ObjectMapper mapper = new ObjectMapper();

    // ------------------------------
    // Deep Normalize List Results
    // ------------------------------
    static Object normalize(Object obj) {

        if (obj instanceof List) {
            List<?> list = (List<?>) obj;
            List<Object> normalized = new ArrayList<>();

            for (Object item : list)
                normalized.add(normalize(item));

            // if list of lists of integers → sort inner lists
            if (!normalized.isEmpty() && normalized.get(0) instanceof List) {

                for (Object inner : normalized)
                    Collections.sort((List<?>) inner);

                normalized.sort((a, b) -> {
                    List<Integer> l1 = (List<Integer>) a;
                    List<Integer> l2 = (List<Integer>) b;
                    for (int i = 0; i < Math.min(l1.size(), l2.size()); i++) {
                        if (!l1.get(i).equals(l2.get(i)))
                            return l1.get(i) - l2.get(i);
                    }
                    return l1.size() - l2.size();
                });
            }

            return normalized;
        }

        return obj;
    }

    // ------------------------------
    // Tree Builder
    // ------------------------------
    static TreeNode buildTree(List<Integer> values) {
        if (values == null || values.isEmpty() || values.get(0) == null)
            return null;

        TreeNode root = new TreeNode(values.get(0));
        Queue<TreeNode> queue = new LinkedList<>();
        queue.add(root);

        int i = 1;

        while (!queue.isEmpty() && i < values.size()) {
            TreeNode node = queue.poll();

            if (i < values.size() && values.get(i) != null) {
                node.left = new TreeNode(values.get(i));
                queue.add(node.left);
            }
            i++;

            if (i < values.size() && values.get(i) != null) {
                node.right = new TreeNode(values.get(i));
                queue.add(node.right);
            }
            i++;
        }

        return root;
    }

    // ------------------------------
    // Linked List Builder
    // ------------------------------
    static ListNode buildList(List<Integer> values, Integer pos) {

        if (values == null || values.isEmpty())
            return null;

        ListNode head = new ListNode(values.get(0));
        ListNode curr = head;

        List<ListNode> nodes = new ArrayList<>();
        nodes.add(head);

        for (int i = 1; i < values.size(); i++) {
            curr.next = new ListNode(values.get(i));
            curr = curr.next;
            nodes.add(curr);
        }

        if (pos != null && pos >= 0 && pos < nodes.size())
            curr.next = nodes.get(pos);

        return head;
    }

    // ------------------------------
    // Graph Builder
    // ------------------------------
    static Node buildGraph(List<List<Integer>> adjList) {

        if (adjList == null || adjList.isEmpty())
            return null;

        Map<Integer, Node> map = new HashMap<>();

        for (int i = 0; i < adjList.size(); i++)
            map.put(i + 1, new Node(i + 1));

        for (int i = 0; i < adjList.size(); i++) {
            Node node = map.get(i + 1);
            for (Integer neighbor : adjList.get(i))
                node.neighbors.add(map.get(neighbor));
        }

        return map.get(1);
    }

    // ------------------------------
    // Invocation
    // ------------------------------
    static Object invoke(String jsonInput) throws Exception {

        Map<String, Object> payload =
            mapper.readValue(jsonInput, new TypeReference<Map<String, Object>>() {});

        String functionName = (String) payload.get("function_name");
        Map<String, Object> input =
            (Map<String, Object>) payload.get("input");

        // ALWAYS new instance per invocation
        Class<?> clazz = Class.forName("Solution");
        Object instance = clazz.getDeclaredConstructor().newInstance();

        Method target = null;
        for (Method m : clazz.getDeclaredMethods()) {
            if (m.getName().equals(functionName)) {
                target = m;
                break;
            }
        }

        if (target == null)
            throw new RuntimeException("Method not found: " + functionName);

        Class<?>[] paramTypes = target.getParameterTypes();
        java.lang.reflect.Parameter[] parameters = target.getParameters();
        Object[] args = new Object[paramTypes.length];

        for (int i = 0; i < paramTypes.length; i++) {
            String paramName = parameters[i].getName();
            Object value = input.get(paramName);
            Class<?> type = paramTypes[i];

            if (type == int[].class) {
                List<Integer> list = (List<Integer>) value;
                int[] arr = new int[list.size()];
                for (int j = 0; j < list.size(); j++)
                    arr[j] = list.get(j);
                args[i] = Arrays.copyOf(arr, arr.length); // deep copy
            }
            else if (type == int.class) {
                args[i] = ((Number) value).intValue();
            }
            else {
                args[i] = value;
            }
        }

        Object result = target.invoke(instance, args);

        return normalize(result);
    }

    // ------------------------------
    // Main
    // ------------------------------
    public static void main(String[] args) {

        try {
            BufferedReader reader =
                new BufferedReader(new InputStreamReader(System.in));

            StringBuilder sb = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null)
                sb.append(line);

            Object result = invoke(sb.toString());

            Map<String, Object> output = new HashMap<>();
            output.put("result", result);

            System.out.println(mapper.writeValueAsString(output));

        } catch (InvocationTargetException e) {

            Throwable cause = e.getCause();
            try {
                System.out.println(
                    mapper.writeValueAsString(
                        Collections.singletonMap("error", cause.toString())
                    )
                );
            } catch (Exception ignored) {}

        } catch (Exception e) {

            try {
                System.out.println(
                    mapper.writeValueAsString(
                        Collections.singletonMap("error", e.toString())
                    )
                );
            } catch (Exception ignored) {}
        }
    }
}
"""
