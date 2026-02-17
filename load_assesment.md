# Unified Runtime Performance Comparison

## Docker-Based Execution Engine

(Python vs JavaScript vs TypeScript)

---

# Light Workload (1 Test Case)

### 20 VUs

| Runtime    | Throughput (RPS) | Avg Latency | p95 Latency | Errors |
| ---------- | ---------------- | ----------- | ----------- | ------ |
| JavaScript | ~12–13           | ~1.35–1.6s  | ~1.6–2s     | 0%     |
| Python     | ~10–11           | ~1.6–1.9s   | ~1.9–2s     | 0%     |
| TypeScript | ~2.4–2.5         | ~7.9s       | ~9.1s       | 0%     |

---

### 10 VUs (TypeScript Stable Zone)

| Runtime    | Throughput (RPS) | Avg Latency | p95 Latency | Errors |
| ---------- | ---------------- | ----------- | ----------- | ------ |
| JavaScript | ~12–13           | ~1.3–1.5s   | <2s         | 0%     |
| Python     | ~10–11           | ~1.6–1.8s   | <2s         | 0%     |
| TypeScript | ~2.46            | ~3.97s      | ~4.36s      | 0%     |

---

# Medium Workload (10–13 Test Cases)

### 20 VUs

| Runtime    | Throughput (RPS) | Avg Latency | p95 Latency | Errors |
| ---------- | ---------------- | ----------- | ----------- | ------ |
| JavaScript | ~7–8             | ~2.5s       | ~2.9s       | 0%     |
| Python     | ~7–8 (est.)      | ~2.5–3s     | ~3s         | 0%     |
| TypeScript | ~2.4–2.5         | ~8s         | ~9s         | 0%     |

---

# High Concurrency (50 VUs)

| Runtime    | Throughput (RPS) | Avg Latency | p95 Latency | Behavior    |
| ---------- | ---------------- | ----------- | ----------- | ----------- |
| JavaScript | ~10              | ~4–5s       | ~6s         | Saturated   |
| Python     | ~9–10            | ~5s         | ~6–8s       | Saturated   |
| TypeScript | ~2.3–2.4         | ~20s        | ~31s        | Queue-heavy |

---

# Throughput Ceiling Summary

| Runtime    | Max Sustainable RPS |
| ---------- | ------------------- |
| JavaScript | ~12–13              |
| Python     | ~10–11              |
| TypeScript | ~2.5                |

---

# Stable Concurrency Range

| Runtime    | Stable VUs |
| ---------- | ---------- |
| JavaScript | ≤20        |
| Python     | ≤20        |
| TypeScript | ≤10        |

---

# Relative Performance Ranking

### Fastest → Slowest (Light Workload)

1. JavaScript
2. Python
3. TypeScript

---
