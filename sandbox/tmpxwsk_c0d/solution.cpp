

#include <iostream>
#include <string>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

extern "C" {
int add(int a, int b);
}

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

int main() {

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

    int a = j["a"];
        int b = j["b"];

    // ==================================================
    // FUNCTION INVOCATION
    // ==================================================

    auto result = add(a, b);

    // ==================================================
    // RETURN SERIALIZATION
    // ==================================================

    json output;

    output = result;

    cout << output.dump();

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

int add(int a, int b) { return a + b; }

