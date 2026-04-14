import http from "k6/http";
import { check } from "k6";
import { Rate, Trend } from "k6/metrics";

// --- Custom metrics ---
const failureRate = new Rate("failures");
const latencyTrend = new Trend("latency");

export const options = {
  scenarios: {
    constant_rps: {
      executor: "constant-arrival-rate",
      rate: 10, // 20 requests per second
      timeUnit: "1s",
      duration: "1m", // run for 1 minute
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    failures: ["rate<0.1"], // optional: keep failure visibility
  },
};

const url = "http://103.173.99.217:8000/execute";

const payload = JSON.stringify({
  language: "cpp",
  source_code:
    "bool hasCycle(ListNode* head) { ListNode *slow=head,*fast=head; while(fast && fast->next){ slow=slow->next; fast=fast->next->next; if(slow==fast) return true;} return false; }",
  function_name: "hasCycle",
  test_cases: [
    {
      input: { head: [1, 2, 3, 4] },
      expected_output: false,
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

  latencyTrend.add(res.timings.duration);

  const success = check(res, {
    "status is 200": (r) => r.status === 200,
  });

  failureRate.add(!success);
}
