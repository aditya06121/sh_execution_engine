GO_WRAPPER_TEMPLATE = r"""
package main

import (
    "encoding/json"
    "fmt"
    "io"
    "os"
    "reflect"
    "sort"
    "strings"
)

type payload struct {
    FunctionName string                     `json:"function_name"`
    Input        map[string]json.RawMessage `json:"input"`
}

type output struct {
    Result interface{} `json:"result,omitempty"`
    Error  string      `json:"error,omitempty"`
}

type ListNode struct {
    Val  int
    Next *ListNode
}

type TreeNode struct {
    Val   int
    Left  *TreeNode
    Right *TreeNode
}

type Node struct {
    Val       int
    Neighbors []*Node
}

func toInt(value interface{}) (int, bool) {
    switch v := value.(type) {
    case float64:
        return int(v), true
    case float32:
        return int(v), true
    case int:
        return v, true
    case int32:
        return int(v), true
    case int64:
        return int(v), true
    default:
        return 0, false
    }
}

func buildLinkedList(values []int, pos int) *ListNode {
    if len(values) == 0 {
        return nil
    }

    dummy := &ListNode{}
    curr := dummy
    nodes := make([]*ListNode, 0, len(values))

    for _, v := range values {
        curr.Next = &ListNode{Val: v}
        curr = curr.Next
        nodes = append(nodes, curr)
    }

    if pos >= 0 && pos < len(nodes) {
        nodes[len(nodes)-1].Next = nodes[pos]
    }

    return dummy.Next
}

func linkedListToArray(head *ListNode) []int {
    result := make([]int, 0)
    visited := map[*ListNode]bool{}

    for head != nil && !visited[head] {
        visited[head] = true
        result = append(result, head.Val)
        head = head.Next
    }

    return result
}

func buildTree(values []interface{}) *TreeNode {
    if len(values) == 0 || values[0] == nil {
        return nil
    }

    nodes := make([]*TreeNode, len(values))
    for i, raw := range values {
        if raw == nil {
            continue
        }
        iv, ok := toInt(raw)
        if !ok {
            return nil
        }
        nodes[i] = &TreeNode{Val: iv}
    }

    pos := 1
    for i := 0; i < len(nodes) && pos < len(nodes); i++ {
        if nodes[i] == nil {
            continue
        }
        if pos < len(nodes) {
            nodes[i].Left = nodes[pos]
            pos++
        }
        if pos < len(nodes) {
            nodes[i].Right = nodes[pos]
            pos++
        }
    }

    return nodes[0]
}

func treeToArray(root *TreeNode) []interface{} {
    if root == nil {
        return []interface{}{}
    }

    result := make([]interface{}, 0)
    queue := []*TreeNode{root}

    for len(queue) > 0 {
        curr := queue[0]
        queue = queue[1:]

        if curr == nil {
            result = append(result, nil)
            continue
        }

        result = append(result, curr.Val)
        queue = append(queue, curr.Left, curr.Right)
    }

    for len(result) > 0 && result[len(result)-1] == nil {
        result = result[:len(result)-1]
    }

    return result
}

func buildGraph(adjList [][]int) *Node {
    if len(adjList) == 0 {
        return nil
    }

    nodes := make([]*Node, len(adjList))
    for i := range adjList {
        nodes[i] = &Node{Val: i + 1}
    }

    for i, neighbors := range adjList {
        for _, n := range neighbors {
            if n >= 1 && n <= len(nodes) {
                nodes[i].Neighbors = append(nodes[i].Neighbors, nodes[n-1])
            }
        }
    }

    return nodes[0]
}

func graphToAdjList(node *Node) [][]int {
    if node == nil {
        return [][]int{}
    }

    visited := map[*Node]bool{}
    queue := []*Node{node}
    ordered := make([]*Node, 0)
    maxVal := 0

    for len(queue) > 0 {
        curr := queue[0]
        queue = queue[1:]

        if curr == nil || visited[curr] {
            continue
        }

        visited[curr] = true
        ordered = append(ordered, curr)
        if curr.Val > maxVal {
            maxVal = curr.Val
        }

        for _, neighbor := range curr.Neighbors {
            if neighbor != nil && !visited[neighbor] {
                queue = append(queue, neighbor)
            }
        }
    }

    sort.Slice(ordered, func(i, j int) bool {
        return ordered[i].Val < ordered[j].Val
    })

    result := make([][]int, maxVal)
    for _, curr := range ordered {
        row := make([]int, 0, len(curr.Neighbors))
        for _, neighbor := range curr.Neighbors {
            if neighbor != nil {
                row = append(row, neighbor.Val)
            }
        }
        result[curr.Val-1] = row
    }

    return result
}

func autoConvertOutput(value interface{}) interface{} {
    switch v := value.(type) {
    case *ListNode:
        return linkedListToArray(v)
    case ListNode:
        vv := v
        return linkedListToArray(&vv)
    case *TreeNode:
        return treeToArray(v)
    case TreeNode:
        vv := v
        return treeToArray(&vv)
    case *Node:
        return graphToAdjList(v)
    case Node:
        vv := v
        return graphToAdjList(&vv)
    default:
        return normalizeGenericOutput(value)
    }
}

func normalizeGenericOutput(value interface{}) interface{} {
    if value == nil {
        return nil
    }

    rv := reflect.ValueOf(value)
    if rv.Kind() == reflect.Slice && rv.IsNil() {
        return []interface{}{}
    }

    return value
}

{source_code}

func execute(input map[string]json.RawMessage) (interface{}, error) {
__PARAM_BINDINGS_PLACEHOLDER__

__INVOKER_SETUP_PLACEHOLDER__
__CALL_PLACEHOLDER__
}

func main() {
    raw, err := io.ReadAll(os.Stdin)
    if err != nil {
        _ = json.NewEncoder(os.Stdout).Encode(output{Error: "failed to read input"})
        os.Exit(1)
    }

    if len(strings.TrimSpace(string(raw))) == 0 {
        _ = json.NewEncoder(os.Stdout).Encode(output{Error: "no input provided"})
        os.Exit(1)
    }

    var p payload
    if err := json.Unmarshal(raw, &p); err != nil {
        _ = json.NewEncoder(os.Stdout).Encode(output{Error: "invalid JSON input"})
        os.Exit(1)
    }

    if p.FunctionName != "" && p.FunctionName != "__FUNCTION_NAME_PLACEHOLDER__" {
        _ = json.NewEncoder(os.Stdout).Encode(output{
            Error: fmt.Sprintf("function '%s' not found", p.FunctionName),
        })
        os.Exit(1)
    }

    result, execErr := execute(p.Input)
    if execErr != nil {
        _ = json.NewEncoder(os.Stdout).Encode(output{Error: execErr.Error()})
        os.Exit(1)
    }

    if err := json.NewEncoder(os.Stdout).Encode(output{Result: result}); err != nil {
        _ = json.NewEncoder(os.Stdout).Encode(output{Error: "failed to serialize output"})
        os.Exit(1)
    }
}
"""
