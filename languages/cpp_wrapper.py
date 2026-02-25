CPP_WRAPPER_TEMPLATE = r"""

#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

// ======================================================
// LeetCode Built-in Data Structures
// ======================================================

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// ======================================================
// Linked List Utilities
// ======================================================

ListNode* buildLinkedList(const vector<int>& values) {
    if (values.empty()) return nullptr;

    ListNode* head = new ListNode(values[0]);
    ListNode* current = head;

    for (size_t i = 1; i < values.size(); ++i) {
        current->next = new ListNode(values[i]);
        current = current->next;
    }

    return head;
}

vector<int> serializeLinkedList(ListNode* head) {
    vector<int> result;
    while (head) {
        result.push_back(head->val);
        head = head->next;
    }
    return result;
}

// ======================================================
// Binary Tree Utilities (Level Order)
// ======================================================

TreeNode* buildTree(const vector<optional<int>>& arr) {
    if (arr.empty() || !arr[0].has_value())
        return nullptr;

    TreeNode* root = new TreeNode(arr[0].value());
    queue<TreeNode*> q;
    q.push(root);

    int i = 1;

    while (!q.empty() && i < arr.size()) {
        TreeNode* current = q.front();
        q.pop();

        if (i < arr.size() && arr[i].has_value()) {
            current->left = new TreeNode(arr[i].value());
            q.push(current->left);
        }
        i++;

        if (i < arr.size() && arr[i].has_value()) {
            current->right = new TreeNode(arr[i].value());
            q.push(current->right);
        }
        i++;
    }

    return root;
}

// 🔥 FIXED: Return json instead of vector<optional<int>>
json serializeTree(TreeNode* root) {

    if (!root) return json::array();

    vector<optional<int>> temp;
    queue<TreeNode*> q;
    q.push(root);

    while (!q.empty()) {
        TreeNode* node = q.front();
        q.pop();

        if (node) {
            temp.push_back(node->val);
            q.push(node->left);
            q.push(node->right);
        } else {
            temp.push_back(nullopt);
        }
    }

    while (!temp.empty() && !temp.back().has_value())
        temp.pop_back();

    json result = json::array();

    for (auto &v : temp) {
        if (v.has_value())
            result.push_back(v.value());
        else
            result.push_back(nullptr);
    }

    return result;
}

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

__FUNCTION_SIGNATURE_PLACEHOLDER__

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

int main() {
    try {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        string input;
        if (!getline(cin, input)) {
            cout << "{\"error\":\"No input received\"}";
            return 1;
        }

        json j;

        try {
            j = json::parse(input);
        } catch (...) {
            cout << "{\"error\":\"Invalid JSON input\"}";
            return 1;
        }

        // ==================================================
        // PARAMETER DESERIALIZATION (AUTO-GENERATED)
        // ==================================================

        __PARAMETER_DESERIALIZATION_PLACEHOLDER__

        // ==================================================
        // FUNCTION INVOCATION
        // ==================================================

        auto result = __FUNCTION_NAME_PLACEHOLDER__(
            __FUNCTION_ARGUMENT_LIST_PLACEHOLDER__
        );

        // ==================================================
        // RETURN TYPE SERIALIZATION
        // ==================================================

        json output;

        __RETURN_SERIALIZATION_PLACEHOLDER__

        cout << output.dump();

    } catch (const exception& e) {
        cout << "{\"error\":\"" << e.what() << "\"}";
        return 1;
    } catch (...) {
        cout << "{\"error\":\"Unknown runtime error\"}";
        return 1;
    }

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

__USER_CODE_PLACEHOLDER__

"""