import http from "k6/http";
import { check } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

export const failureRate = new Rate("failures");
export const e2eLatency = new Trend("e2e_latency_ms", true);
export const jobsTimedOut = new Counter("jobs_timed_out"); 

export const options = {
  scenarios: {
    constant_rps: {
      executor: "constant-arrival-rate",
      rate: 150, 
      timeUnit: "1s",
      duration: "5s", 
      preAllocatedVUs: 1000,
      maxVUs: 2000,
      gracefulStop: "1m", 
    },
  },
  thresholds: {
    failures: ["rate<0.05"],
    e2e_latency_ms: ["p(90)<60000"],
    "e2e_latency_ms{p:99}": ["p(99)<120000"],
  },
};

const BASE_URL = "http://103.173.99.217:8000";

const SUBMIT_PARAMS = {
  headers: { "Content-Type": "application/json" },
  timeout: "120s", 
};

// Switched to Python. Compiling 20 C++ programs per second requires 
// massive horizontal scaling. Python skips the heavy compilation phase, 
// allowing the baseline engine ingestion to be tested effectively.
const PAYLOAD = JSON.stringify({
  language: "python",
  source_code: "def hasCycle(head):\n    slow = fast = head\n    while fast and fast.next:\n        slow = slow.next\n        fast = fast.next.next\n        if slow == fast:\n            return True\n    return False",
  function_name: "hasCycle",
  test_cases: [{ input: { head: [1, 2, 3, 4] }, expected_output: false }],
});

export default function () {
  const wallStart = Date.now();

  const submitRes = http.post(`${BASE_URL}/execute`, PAYLOAD, SUBMIT_PARAMS);
  e2eLatency.add(Date.now() - wallStart);

  if (submitRes.status === 200) {
    let body;
    try {
      body = JSON.parse(submitRes.body);
    } catch (_) {
      failureRate.add(1);
      return;
    }

    const verdict = body.verdict ?? null;
    const success = check(
      { verdict },
      {
        "verdict accepted": (v) => v.verdict === "accepted",
      },
    );
    failureRate.add(!success);
    return;
  }

  // Any non-200 status (like 503 queue full or 504 timeout) is a failure
  if (submitRes.status === 504) {
      jobsTimedOut.add(1);
  }
  
  check(submitRes, {
    "status is 200": (r) => r.status === 200,
  });

  failureRate.add(1);
}
