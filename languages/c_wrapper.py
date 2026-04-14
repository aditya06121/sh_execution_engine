C_WRAPPER_TEMPLATE = r"""

#include <iostream>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

extern "C" {
__FUNCTION_SIGNATURE_PLACEHOLDER__
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

    __PARAMETER_DESERIALIZATION_PLACEHOLDER__

    // ==================================================
    // FUNCTION INVOCATION
    // ==================================================

    __FUNCTION_CALL_PLACEHOLDER__

    // ==================================================
    // RETURN SERIALIZATION
    // ==================================================

    json output;

    __RETURN_SERIALIZATION_PLACEHOLDER__

    cout << output.dump();

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

__USER_CODE_PLACEHOLDER__

"""