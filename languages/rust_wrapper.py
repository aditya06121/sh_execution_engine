RUST_WRAPPER_TEMPLATE = r"""

use std::io::{self, Read};
use serde_json::{Value, json};

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

__FUNCTION_SIGNATURE_PLACEHOLDER__

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

fn main() {

    // Read stdin
    let mut input = String::new();

    if io::stdin().read_to_string(&mut input).is_err() {
        println!("{{\"error\":\"Failed to read input\"}}");
        return;
    }

    let j: Value = match serde_json::from_str(&input) {
        Ok(v) => v,
        Err(_) => {
            println!("{{\"error\":\"Invalid JSON input\"}}");
            return;
        }
    };

    // ==================================================
    // PARAMETER DESERIALIZATION (AUTO-GENERATED)
    // ==================================================

    __PARAMETER_DESERIALIZATION_PLACEHOLDER__

    // ==================================================
    // FUNCTION INVOCATION
    // ==================================================

    let result = __FUNCTION_NAME_PLACEHOLDER__(
        __FUNCTION_ARGUMENT_LIST_PLACEHOLDER__
    );

    // ==================================================
    // RETURN SERIALIZATION
    // ==================================================

    let output = {
        __RETURN_SERIALIZATION_PLACEHOLDER__
    };

    println!("{}", serde_json::to_string(&output).unwrap());
}

// ======================================================
// USER CODE INJECTION
// ======================================================

__USER_CODE_PLACEHOLDER__

"""