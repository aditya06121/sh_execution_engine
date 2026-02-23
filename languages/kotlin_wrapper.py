KOTLIN_WRAPPER_TEMPLATE = r"""
import java.io.BufferedReader
import java.io.InputStreamReader
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import java.util.*
import com.fasterxml.jackson.databind.ObjectMapper
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
// Helper Builders
// ==============================

object Builders {

    fun buildTree(values: List<Int?>?): TreeNode? {
        if (values == null || values.isEmpty()) return null

        val nodes = values.map { if (it == null) null else TreeNode(it) }
        val root = nodes[0]
        val queue: Queue<TreeNode?> = LinkedList()
        queue.offer(root)

        var i = 1
        while (queue.isNotEmpty() && i < nodes.size) {
            val current = queue.poll()
            if (current != null) {
                current.left = nodes[i++]
                if (i < nodes.size) current.right = nodes[i++]
                queue.offer(current.left)
                queue.offer(current.right)
            }
        }

        return root
    }

    fun treeToList(root: TreeNode?): List<Int?> {
        if (root == null) return emptyList()

        val result = mutableListOf<Int?>()
        val queue: Queue<TreeNode?> = LinkedList()
        queue.offer(root)

        while (queue.isNotEmpty()) {
            val node = queue.poll()
            if (node != null) {
                result.add(node.`val`)
                queue.offer(node.left)
                queue.offer(node.right)
            } else {
                result.add(null)
            }
        }

        while (result.isNotEmpty() && result.last() == null)
            result.removeAt(result.size - 1)

        return result
    }

    fun buildLinkedList(values: List<Int>?, pos: Int): ListNode? {
        if (values == null || values.isEmpty()) return null

        val dummy = ListNode(0)
        var curr = dummy
        val nodes = mutableListOf<ListNode>()

        for (v in values) {
            curr.next = ListNode(v)
            curr = curr.next!!
            nodes.add(curr)
        }

        if (pos != -1 && pos < nodes.size)
            curr.next = nodes[pos]

        return dummy.next
    }

    fun linkedListToList(head: ListNode?): List<Int> {
        val result = mutableListOf<Int>()
        val visited = HashSet<ListNode>()
        var curr = head

        while (curr != null && !visited.contains(curr)) {
            visited.add(curr)
            result.add(curr.`val`)
            curr = curr.next
        }

        return result
    }

    fun buildGraph(adj: List<List<Int>>?): Node? {
        if (adj == null || adj.isEmpty()) return null

        val nodes = HashMap<Int, Node>()
        for (i in adj.indices)
            nodes[i + 1] = Node(i + 1)

        for (i in adj.indices)
            for (n in adj[i])
                nodes[i + 1]!!.neighbors.add(nodes[n]!!)

        return nodes[1]
    }

    fun graphToAdjList(node: Node?): List<List<Int>> {
        if (node == null) return emptyList()

        val visited = HashSet<Node>()
        val queue: Queue<Node> = LinkedList()
        val nodes = mutableListOf<Node>()

        queue.offer(node)

        while (queue.isNotEmpty()) {
            val curr = queue.poll()
            if (visited.contains(curr)) continue

            visited.add(curr)
            nodes.add(curr)

            for (n in curr.neighbors)
                if (!visited.contains(n))
                    queue.offer(n)
        }

        nodes.sortBy { it.`val` }

        val maxVal = nodes.maxOf { it.`val` }
        val result = MutableList(maxVal) { mutableListOf<Int>() }

        for (curr in nodes)
            for (n in curr.neighbors)
                result[curr.`val` - 1].add(n.`val`)

        return result
    }
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Execution Engine
// ==============================

object Main {

    private val mapper = ObjectMapper()

    private fun autoConvertOutput(result: Any?): Any? {
        return when (result) {
            is TreeNode -> Builders.treeToList(result)
            is ListNode -> Builders.linkedListToList(result)
            is Node -> Builders.graphToAdjList(result)
            else -> result
        }
    }

    private fun convertValue(value: Any?, targetType: Class<*>, fullInput: Map<String, Any?>): Any? {

        if (value == null) return null

        if (targetType == Int::class.java || targetType == Integer.TYPE)
            return (value as Number).toInt()

        if (targetType == Long::class.java || targetType == java.lang.Long.TYPE)
            return (value as Number).toLong()

        if (targetType == Double::class.java || targetType == java.lang.Double.TYPE)
            return (value as Number).toDouble()

        if (targetType == Boolean::class.java || targetType == java.lang.Boolean.TYPE)
            return value

        if (targetType == String::class.java)
            return value.toString()

        if (targetType == IntArray::class.java) {
            val list = value as List<*>
            return list.map { (it as Number).toInt() }.toIntArray()
        }

        if (targetType == Array<IntArray>::class.java) {
            val outer = value as List<*>
            return outer.map {
                (it as List<*>).map { n -> (n as Number).toInt() }.toIntArray()
            }.toTypedArray()
        }

        if (targetType == TreeNode::class.java)
            return Builders.buildTree(value as List<Int?>)

        if (targetType == ListNode::class.java) {
            val pos = (fullInput["pos"] as? Number)?.toInt() ?: -1
            return Builders.buildLinkedList(value as List<Int>, pos)
        }

        if (targetType == Node::class.java)
            return Builders.buildGraph(value as List<List<Int>>)

        return value
    }

    private fun executeFunction(functionName: String, input: Map<String, Any?>): Any? {

        try {
            val solutionClass = Class.forName("Solution")
            val instance = solutionClass.getDeclaredConstructor().newInstance()

            for (method in solutionClass.declaredMethods) {

                if (method.name != functionName) continue

                val paramTypes = method.parameterTypes
                val values = ArrayList(input.values)
                val args = Array<Any?>(paramTypes.size) { null }

                for (i in paramTypes.indices)
                    args[i] = convertValue(values[i], paramTypes[i], input)

                val result = method.invoke(instance, *args)
                return autoConvertOutput(result)
            }

        } catch (e: InvocationTargetException) {
            throw Exception(e.targetException.message)
        }

        throw Exception("Function '$functionName' not found")
    }

    @JvmStatic
    fun main(args: Array<String>) {

        try {
            val reader = BufferedReader(InputStreamReader(System.`in`))
            val inputBuilder = StringBuilder()
            var line: String?

            while (reader.readLine().also { line = it } != null)
                inputBuilder.append(line)

            val payload: Map<String, Any?> =
                mapper.readValue(inputBuilder.toString(),
                    object : TypeReference<Map<String, Any?>>() {})

            val functionName = payload["function_name"] as String
            val input = payload["input"] as Map<String, Any?>

            val result = executeFunction(functionName, input)

            val response = HashMap<String, Any?>()
            response["result"] = result

            println(mapper.writeValueAsString(response))

        } catch (e: Exception) {

            try {
                val error = HashMap<String, Any?>()
                error["error"] = e.message
                println(mapper.writeValueAsString(error))
            } catch (_: Exception) {}

            System.exit(1)
        }
    }
}
"""