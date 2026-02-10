# Domain-Restricted Execution Engine

## Security-First Design & Implementation Guidelines

This document defines a **chronological, non-negotiable roadmap** for building a
**domain-restricted execution engine** with a **minimal attack surface**, suitable for
**production deployment** and **academic publication**.

The goal is not general-purpose code execution, but a **deliberately constrained execution primitive**
designed for shell-based validation tasks (e.g., Terraform validation).

---

## Design Philosophy

> Reduced capability is a security feature, not a limitation.

This system prioritizes:

- Explicit contracts over flexibility
- Kernel-enforced isolation over application-level checks
- Deterministic behavior over convenience
- Narrow scope over extensibility

---

## Phase 0 — Problem Framing (Before Any Code)

### 0.1 Execution Contract (Non-Negotiable)

This contract defines the **security boundary**, **implementation scope**, and **research claims**.

#### Allowed

- Shell commands (strict allowlist)
- Shell scripts
- `terraform validate -no-color`

#### Disallowed

- Network access
- Compilation or build tools
- Background processes
- Persistent storage
- Root privileges

This contract must be enforced **by design**, not by convention.

---

### 0.2 Threat Model (Design-Driving)

A formal threat model must be created **before implementation**.

#### Assets

- Host operating system
- Other tenants / executions
- Terraform providers
- Execution output integrity

#### Threats

- Denial of Service (fork bombs, infinite loops)
- Sandbox escape
- Cross-tenant data access
- Supply-chain abuse (provider downloads)

#### Output

- STRIDE-style threat → mitigation mapping

This mapping directly informs:

- Jail configuration
- Filesystem layout
- API boundaries
- Resource limits

---

## Phase 1 — Execution Isolation Core (Foundation)

### 1.1 Minimal Execution Image

Create a **minimal root filesystem**:

- BusyBox or Alpine-based
- Only required binaries:
  - `sh`
  - coreutils
  - `terraform`
- Terraform providers pre-installed

Explicit exclusions:

- No package managers
- No `curl` / `wget`
- No compilers or build tools

This minimizes both attack surface and startup latency.

---

### 1.2 User and Namespace Isolation

Each execution must run with:

- Non-root user
- User namespace
- PID namespace
- Mount namespace

Goal:

> Even a fully compromised process has no meaningful privileges.

---

### 1.3 Filesystem Lockdown

Enforce:

- Read-only root filesystem (`/`)
- Writable `/tmp` only
- No access to `/proc`, `/sys`, `/dev`
- No host filesystem mounts

This prevents:

- Host inspection
- Kernel interaction
- Cross-execution leakage

---

### 1.4 Resource Limits

All limits must be enforced at the **kernel level**:

- CPU time
- Memory
- Maximum process count
- Maximum file size
- Wall-clock timeout

This is mandatory DoS protection.

---

## Phase 2 — Secure Execution Engine

### 2.1 Command Validation Layer

Before execution:

- Parse input tokens
- Reject:
  - `;`, `&&`, `||`
  - `$()`
  - backticks
  - output/input redirection (unless explicitly allowed)

Validation must be:

- Token-based (not regex-only)
- Per-command allowlisted

Purpose: eliminate command chaining and shell injection.

---

### 2.2 Execution Wrapper

Implement a runner that:

- Spawns a new jail per request
- Injects input files
- Executes the validated command
- Captures stdout and stderr
- Enforces hard timeouts

Design constraints:

- One request → one jailed process
- No shared state between executions

---

### 2.3 Terraform-Specific Restrictions

Terraform execution must be explicitly constrained:

- Only allow:
  ```bash
  terraform validate -no-color
  ```

````

- Disable:
  - Backends
  - `init`
  - `apply`

- Providers must be local-only

Terraform defaults are not safe and must never be trusted.

---

## Phase 3 — API and Job Control

### 3.1 Stateless Execution API

API characteristics:

- Accepts:
  - Command type
  - Input files

- Returns:
  - stdout
  - stderr
  - exit code
  - execution metadata

Constraints:

- No sessions
- No persistent jobs

Stateless design improves security and scalability.

---

### 3.2 Job Lifecycle Management

Implement:

- Job queue (in-memory initially)
- Fixed worker pool
- Forced termination on timeout

Benefits:

- Load control
- Backpressure
- Predictable behavior

---

### 3.3 Auditing and Logging

Log the following:

- Requested command
- Execution duration
- Resource usage
- Exit reason (success, timeout, killed)

Logs are essential for:

- Incident analysis
- Security audits
- Research evaluation

---

## Phase 4 — Hardening and Abuse Resistance

### 4.1 Network Isolation

Enforce:

- Network namespace isolation
- No loopback
- No DNS
- No Unix sockets

This eliminates:

- Data exfiltration
- Botnet usage
- Supply-chain attacks

---

### 4.2 Syscall Filtering

Apply:

- Seccomp profiles
- Explicit syscall allowlist

Even with remote code execution, kernel access remains blocked.

---

### 4.3 Failure Containment Testing

Actively test:

- Fork bombs
- Infinite loops
- Large file writes
- Path traversal
- Terraform abuse scenarios

Record:

- Host stability
- Jail termination behavior
- Any data leakage

These results form part of the research evaluation.

---

## Phase 5 — Production Readiness

### 5.1 Concurrency and Scaling Model

Define:

- Maximum concurrent jobs
- Per-worker jail limits
- Horizontal scaling strategy

Initial recommendation:

- Fixed worker pool
- No auto-scaling

---

### 5.2 Observability

Expose metrics:

- Execution latency
- Failure rates
- Resource exhaustion events

Observability is mandatory for production systems.

---

### 5.3 Security Posture Documentation

Document:

- Trust boundaries
- Threat assumptions
- Known limitations

This documentation serves both operational and academic purposes.

---

## Phase 6 — Research Evaluation

### 6.1 Comparative Analysis

Compare against general-purpose engines (e.g., Judge-style systems):

- Startup latency
- Memory footprint
- Attack surface size
- Supported capabilities

Primary claim:

> Reduced capability leads to increased security and predictability.

---

### 6.2 Reproducibility

Ensure:

- Deterministic execution
- Fixed versions
- Repeatable benchmarks

Reproducibility is critical for peer review.

---

### 6.3 Research Artifacts

Prepare:

- Architecture diagrams
- Threat model tables
- Evaluation graphs
- Failure case studies

---

## Phase 7 — Paper Writing Order

Recommended writing sequence:

1. Problem statement and motivation
2. Threat model
3. System design
4. Implementation details
5. Evaluation
6. Limitations
7. Related work

Related work should be written last.

---

## Completion Milestones

- Phase 3 complete → Functional MVP
- Phase 5 complete → Production-grade system
- Phase 6 complete → Publishable research artifact

---

## Final Note

This system is not a general sandbox.
It is a **security-first execution primitive** designed for constrained, high-assurance use cases.

Build less. Enforce more.

```

---
```
````
