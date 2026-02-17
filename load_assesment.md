Here is your **Unified Load Testing Overview Document** covering both **Python and JavaScript execution engines**, light and heavier workloads, and all observed behavior.

---

# Unified Performance & Load Testing Overview

## Docker-Based Code Execution Engine (Python + JavaScript)

---

# 1. System Overview

The system under test is a container-based code execution engine supporting multiple runtimes (Python and JavaScript).

### Core Behavior

- Accepts code via HTTP POST (`/execute`)
- Spawns a Docker container per request
- Executes user-submitted code
- Runs test cases
- Returns structured results
- Destroys container after execution

### Current Architecture

```
Client → FastAPI → Docker spawn → Runtime (Python/Node) → Execute test cases → Destroy container → Response
```

### Design Principles

- Strong isolation
- Stateless execution
- Clean teardown per request
- Security-first execution model

---

# 2. Load Testing Methodology

Testing tool: **k6**

### Scenarios Executed

| Scenario | Concurrency     | Duration   |
| -------- | --------------- | ---------- |
| A        | 20 constant VUs | 60 seconds |
| B        | 50 constant VUs | 60 seconds |

### Workload Variants Tested

1. Light workload (1 test case)
2. Medium workload (10 test cases)
3. Python runtime
4. JavaScript runtime

This allowed evaluation of:

- Cold start impact
- Runtime overhead differences
- Execution scaling behavior
- Throughput ceiling
- Latency growth under saturation

---

# 3. Observed Results Summary

---

## A. JavaScript – 1 Test Case – 20 VUs

- Throughput: ~12.8 RPS
- Avg latency: ~1.35s
- p95: ~1.64s
- Errors: 0%

System stable and within performance threshold.

---

## B. Python – 1 Test Case – 20 VUs

- Throughput: ~10.6 RPS
- Avg latency: ~1.66s
- p95: ~1.95s
- Errors: 0%

Stable, slightly slower than JS runtime.

---

## C. JavaScript – 10 Test Cases – 20 VUs

- Throughput: ~7.3 RPS
- Avg latency: ~2.51s
- p95: ~2.93s
- Errors: 0%

Execution workload begins affecting throughput significantly.

---

## D. JavaScript – 50 VUs

- Throughput: ~10 RPS (light workload)
- Avg latency: ~4.67s
- p95: ~6.57s
- Errors: 0%

System saturated.
Latency increased sharply.
Throughput plateaued.

---

# 4. Throughput Ceiling Analysis

Across all tests:

| Workload           | Max Sustainable RPS |
| ------------------ | ------------------- |
| JS (light)         | ~12–13 RPS          |
| Python (light)     | ~10–11 RPS          |
| JS (10 test cases) | ~7–8 RPS            |

Increasing concurrency beyond capacity:

- Did NOT increase throughput
- Only increased latency

This confirms:

> The system is throughput-bound, not concurrency-bound.

---

# 5. Throughput-Bound Behavior Explained

Using Little’s Law:

```
Concurrency = Throughput × Response Time
```

Rearranged:

```
Response Time = Concurrency / Throughput
```

Example:

At 50 VUs and ~10 RPS capacity:

```
Response Time ≈ 50 / 10 ≈ 5 seconds
```

Observed latency:
~4.6–5.2 seconds

The system follows queueing theory precisely.

---

# 6. Root Cause of Bottlenecks

Primary constraints:

1. Docker container creation per request
2. Runtime cold start cost
3. Docker daemon serialization
4. CPU core limitation
5. Increased execution cost as test cases grow

For light workloads:
Cold start dominates.

For heavier workloads:
Cold start + execution time both contribute.

---

# 7. Runtime Comparison

| Runtime    | Performance Observation           |
| ---------- | --------------------------------- |
| JavaScript | Slightly faster cold start        |
| Python     | Slightly heavier startup overhead |

However:

Language choice does NOT change throughput ceiling dramatically.

Architecture dominates.

---

# 8. Behavior Under Burst Traffic (50 RPS Scenario)

If incoming traffic spikes to:

50 requests/sec

And system capacity is:

~7–12 RPS (depending on workload)

Backlog growth rate:

```
50 - capacity
```

For 10-test workload (~7 RPS):

```
50 - 7 = 43 requests queued per second
```

In 5 seconds:
215 requests queued.

Expected user latency:
5–10+ seconds.

System will not crash.
It will queue.

---

# 9. Architectural Characteristics

Current design provides:

✔ Strong isolation
✔ Clean stateless execution
✔ Predictable degradation under overload
✔ Zero request failures under stress

---

# 10. Cost Consideration

Container-per-request model is:

Highly efficient at:

- Low traffic
- Idle periods
- Small usage patterns

Less efficient during:

- Burst traffic
- Sustained high concurrency
- CPU-heavy workloads

Because:

- Docker spawn is CPU expensive
- Overhead multiplies under concurrency
- Larger instance sizes may be required

---

# 11. Final Conclusions

The execution engine is:

Stable, secure, and predictable.

It performs well under:

≤ 20 concurrent users
≤ 10–12 RPS

Under heavier workload (10 test cases):

Sustainable capacity drops to:

~7 RPS

Under 50 concurrent users:

- Throughput plateaus
- Latency increases significantly
- No crashes occur
- System becomes queue-bound

---

# 12. Overall System Classification

The system is:

> Throughput-bound at the container orchestration layer.

Not network-bound.
Not framework-bound.
Not language-bound.

The limiting factor is per-request container lifecycle cost.

---

# Executive Summary

- Maximum sustainable throughput: 7–12 RPS depending on workload
- Stable under moderate load
- Predictable saturation behavior
- Cold start overhead dominates performance
- Execution complexity directly reduces throughput ceiling

The system is production-ready for:

- Low to moderate traffic
- Internal tools
- Controlled environments

It is not currently optimized for:

- High burst traffic (50+ RPS)
- Public competitive coding scale
- High-concurrency SaaS workloads

---
