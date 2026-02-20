KOTLIN_WRAPPER_TEMPLATE=r"""
import java.io.*
import java.lang.reflect.*
import java.util.*
import com.fasterxml.jackson.databind.*
import com.fasterxml.jackson.core.type.TypeReference

// ==============================
// Built-in Data Structures
// ==============================

class TreeNode(var `val`: Int) {
    var left: TreeNode? = null
    var right: TreeNode? = null
}

class ListNode(var `val`: Int) {
    var next: ListNode? = null
}

class Node(var `val`: Int) {
    var neighbors: MutableList<Node> = ArrayList()
}

// ==============================
// User Code
// ==============================

{USER_CODE}

// ==============================
// Execution Engine
// ==============================

object MainKt {

    private val mapper = ObjectMapper()

    // ------------------------------
    // Tree Builder
    // ------------------------------
    private fun buildTree(values: List<Int?>?): TreeNode? {

        if (values == null || values.isEmpty() || values[0] == null)
            return null

        val root = TreeNode(values[0]!!)
        val queue: Queue<TreeNode> = LinkedList()
        queue.add(root)

        var i = 1

        while (queue.isNotEmpty() && i < values.size) {
            val node = queue.poll()

            if (i < values.size && values[i] != null) {
                node.left = TreeNode(values[i]!!)
                queue.add(node.left)
            }
            i++

            if (i < values.size && values[i] != null) {
                node.right = TreeNode(values[i]!!)
                queue.add(node.right)
            }
            i++
        }

        return root
    }

    // ------------------------------
    // Linked List Builder
    // ------------------------------
    private fun buildList(values: List<Int>?, pos: Int?): ListNode? {

        if (values == null || values.isEmpty())
            return null

        val head = ListNode(values[0])
        var curr = head

        val nodes = mutableListOf<ListNode>()
        nodes.add(head)

        for (i in 1 until values.size) {
            curr.next = ListNode(values[i])
            curr = curr.next!!
            nodes.add(curr)
        }

        if (pos != null && pos >= 0 && pos < nodes.size)
            curr.next = nodes[pos]

        return head
    }

    // ------------------------------
    // Graph Builder
    // ------------------------------
    private fun buildGraph(adj: List<List<Int>>?): Node? {

        if (adj == null || adj.isEmpty())
            return null

        val map = HashMap<Int, Node>()

        for (i in adj.indices)
            map[i + 1] = Node(i + 1)

        for (i in adj.indices) {
            val node = map[i + 1]!!
            for (nei in adj[i])
                node.neighbors.add(map[nei]!!)
        }

        return map[1]
    }

    // ------------------------------
    // Graph to Adj List
    // ------------------------------
    private fun graphToAdj(node: Node?): List<List<Int>> {

        if (node == null)
            return emptyList()

        val map = HashMap<Int, Node>()
        val queue: Queue<Node> = LinkedList()
        val visited = HashSet<Int>()

        queue.add(node)
        map[node.`val`] = node

        while (queue.isNotEmpty()) {
            val curr = queue.poll()

            if (!visited.add(curr.`val`))
                continue

            for (nei in curr.neighbors) {
                if (!map.containsKey(nei.`val`)) {
                    map[nei.`val`] = nei
                    queue.add(nei)
                }
            }
        }

        val size = map.size
        val result = MutableList(size) { mutableListOf<Int>() }

        for (i in 1..size) {
            val curr = map[i]
            curr?.neighbors?.forEach {
                result[i - 1].add(it.`val`)
            }
        }

        return result
    }

    // ------------------------------
    // ListNode to Array
    // ------------------------------
    private fun listToArray(head: ListNode?): List<Int> {

        val result = mutableListOf<Int>()
        val visited = HashSet<ListNode>()

        var curr = head

        while (curr != null && visited.add(curr)) {
            result.add(curr.`val`)
            curr = curr.next
        }

        return result
    }

    // ------------------------------
    // Tree to Level Order
    // ------------------------------
    private fun treeToArray(root: TreeNode?): List<Int?> {

        val result = mutableListOf<Int?>()
        if (root == null) return result

        val queue: Queue<TreeNode?> = LinkedList()
        queue.add(root)

        while (queue.isNotEmpty()) {
            val node = queue.poll()

            if (node == null) {
                result.add(null)
                continue
            }

            result.add(node.`val`)
            queue.add(node.left)
            queue.add(node.right)
        }

        while (result.isNotEmpty() && result.last() == null)
            result.removeAt(result.lastIndex)

        return result
    }

    // ------------------------------
    // Invocation
    // ------------------------------
    private fun invoke(jsonInput: String): Any? {

        val payload: Map<String, Any?> =
            mapper.readValue(jsonInput, object : TypeReference<Map<String, Any?>>() {})

        val functionName = payload["function_name"] as String
        val input = payload["input"] as Map<String, Any?>

        val clazz = Class.forName("Solution")
        val instance = clazz.getDeclaredConstructor().newInstance()

        val method = clazz.declaredMethods.firstOrNull {
            it.name == functionName
        } ?: throw RuntimeException("Method not found: $functionName")

        val paramTypes = method.parameterTypes
        val args = arrayOfNulls<Any>(paramTypes.size)

        val posMeta = (input["pos"] as? Number)?.toInt()

        var index = 0

        for ((key, value) in input) {

            if (key == "pos") continue

            when (paramTypes[index]) {
                IntArray::class.java -> {
                    val list = value as List<Int>
                    args[index] = list.toIntArray()
                }
                TreeNode::class.java -> {
                    args[index] = buildTree(value as List<Int?>)
                }
                ListNode::class.java -> {
                    args[index] = buildList(value as List<Int>, posMeta)
                }
                Node::class.java -> {
                    args[index] = buildGraph(value as List<List<Int>>)
                }
                Int::class.javaPrimitiveType -> {
                    args[index] = (value as Number).toInt()
                }
                else -> {
                    args[index] = value
                }
            }
            index++
        }

        val result = method.invoke(instance, *args)

        return when (result) {
            is ListNode -> listToArray(result)
            is TreeNode -> treeToArray(result)
            is Node -> graphToAdj(result)
            else -> result
        }
    }

    // ------------------------------
    // Main
    // ------------------------------
    @JvmStatic
    fun main(args: Array<String>) {

        try {
            val reader = BufferedReader(InputStreamReader(System.`in`))
            val input = reader.readText()

            val result = invoke(input)

            val output = mapOf("result" to result)
            println(mapper.writeValueAsString(output))

        } catch (e: InvocationTargetException) {

            val cause = e.targetException
            println(
                mapper.writeValueAsString(
                    mapOf("error" to cause.toString())
                )
            )

        } catch (e: Exception) {

            println(
                mapper.writeValueAsString(
                    mapOf("error" to e.toString())
                )
            )
        }
    }
}
"""