## TB1 — User → Execution API

Untrusted user input enters trusted control plane

| STRIDE | Threat                | Impact                      | Mitigation                                   |
| ------ | --------------------- | --------------------------- | -------------------------------------------- |
| S      | Identity spoofing     | Unauthorized execution      | AuthN (JWT/mTLS), request signing            |
| T      | Request tampering     | Command/config manipulation | Schema validation, immutable request objects |
| R      | User denies execution | No audit trail              | Not a Risk Factor                            |
| I      | Info disclosure       | Leakage via error messages  | Generic errors, no stack traces              |
| D      | API flooding          | Service unavailability      | Rate limiting, request quotas                |
| E      | Privilege escalation  | User executes as system     | No privilege escalation allowed              |

## TB2 — Control Plane → Sandbox (CRITICAL)

Trusted orchestrator launches attacker-controlled execution

| STRIDE | Threat                     | Impact                  | Mitigation                        |
| ------ | -------------------------- | ----------------------- | --------------------------------- |
| S      | Sandbox identity confusion | Wrong execution context | One-shot execution IDs            |
| T      | Sandbox config tampering   | Weakened isolation      | Immutable jail configs            |
| R      | Execution denial           | Missing auditability    | No need                           |
| I      | Host data exposure         | Secret leakage          | Read-only FS, no env inheritance  |
| D      | Resource exhaustion        | Host DoS                | CPU/mem/PID/time quotas           |
| E      | Sandbox escape             | Host compromise         | Seccomp, user namespaces, no root |

## TB3 — Sandbox → Terraform / LocalStack (Validation Environment)

Execution interacts with tools and simulated services

| STRIDE | Threat                    | Impact              | Mitigation                    |
| ------ | ------------------------- | ------------------- | ----------------------------- |
| S      | Fake provider injection   | Malicious execution | Provider allowlist            |
| T      | Provider binary tampering | Arbitrary code exec | Immutable provider FS         |
| R      | Denied tool actions       | Audit gaps          | no need                       |
| I      | Env variable leakage      | Secret disclosure   | Empty env, explicit injection |
| D      | Tool abuse                | Resource exhaustion | Execution limits              |
| E      | Tool-assisted escape      | Privilege gain      | No network, no exec mounts    |

## TB4 — Sandbox Output → Result Store / User

Attacker-controlled output enters trusted systems

| STRIDE | Threat              | Impact               | Mitigation         |
| ------ | ------------------- | -------------------- | ------------------ |
| S      | Output spoofing     | Fake success/failure | Trusted exit codes |
| T      | Log injection       | Corrupted logs       | Structured logging |
| R      | Execution denial    | No accountability    | no need            |
| I      | Data leakage        | Secrets in logs      | Output filtering   |
| D      | Output flooding     | Storage exhaustion   | Size limits        |
| E      | Result manipulation | False audit trail    | Append-only logs   |
