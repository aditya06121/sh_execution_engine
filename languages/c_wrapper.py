C_WRAPPER_TEMPLATE = r"""
// ======================================================
// AUTO-GENERATED C EXECUTION WRAPPER
// Pure C (C11)
// ======================================================

#include <stdio.h>
#include <stdlib.h>

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

__FUNCTION_SIGNATURE_PLACEHOLDER__

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

int main() {

    // ===========================
    // INPUT DECLARATION
    // ===========================

    __INPUT_DECLARATION_PLACEHOLDER__

    // ===========================
    // INPUT SCANNING
    // ===========================

    __INPUT_SCAN_PLACEHOLDER__

    // ===========================
    // FUNCTION CALL
    // ===========================

    __FUNCTION_CALL_PLACEHOLDER__

    // ===========================
    // OUTPUT PRINT
    // ===========================

    __OUTPUT_PRINT_PLACEHOLDER__

    // ===========================
    // CLEANUP (if needed)
    // ===========================

    __CLEANUP_PLACEHOLDER__

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

__USER_CODE_PLACEHOLDER__

"""