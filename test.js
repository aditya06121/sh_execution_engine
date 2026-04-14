import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Counter, Rate } from "k6/metrics";

// --- Custom metrics ---
const failureRate = new Rate("failures");
const errorCount = new Counter("error_count");
const latencyTrend = new Trend("latency");

export const options = {
  scenarios: {
    ramping_load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 20 },
        { duration: "1m", target: 40 },
        { duration: "1m", target: 60 },
        { duration: "1m", target: 80 },
        { duration: "1m", target: 100 },
        { duration: "1m", target: 120 },
        { duration: "1m", target: 140 },
        { duration: "1m", target: 150 },
      ],
      gracefulRampDown: "30s",
    },
  },

  thresholds: {
    failures: ["rate<0.1"], // fail if >10% failures
    latency: ["p(95)<2000"], // 95% under 2s
  },
};

const url = "http://103.173.99.217:8000/execute";

const payload = JSON.stringify({
  language: "csharp",
  source_code:
    "public class Solution { public int Add(int a, int b) { return a + b; } }",
  function_name: "Add",
  test_cases: [
    {
      input: { a: 2, b: 3 },
      expected_output: 5,
    },
  ],
});

const params = {
  headers: {
    "Content-Type": "application/json",
  },
};

export default function () {
  const res = http.post(url, payload, params);

  const success = check(res, {
    "status 200": (r) => r.status === 200,
    "latency < 2s": (r) => r.timings.duration < 2000,
  });

  // --- Metrics collection ---
  latencyTrend.add(res.timings.duration);
  failureRate.add(!success);

  if (!success) {
    errorCount.add(1);

    // Critical: log with VU + iteration context
    console.error(
      `FAIL | VU=${__VU} ITER=${__ITER} STATUS=${res.status} TIME=${res.timings.duration}ms BODY=${res.body}`,
    );
  }

  // Optional: periodic debug logs (not every request)
  if (__ITER % 50 === 0) {
    console.log(
      `INFO | VU=${__VU} ITER=${__ITER} STATUS=${res.status} TIME=${res.timings.duration}ms`,
    );
  }

  sleep(1);
}
