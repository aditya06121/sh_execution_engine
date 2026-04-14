import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// --- Custom metrics ---
const failureRate = new Rate("failures");
const e2eLatency = new Trend("e2e_latency_ms");  // submit → result ready

export const options = {
  scenarios: {
    constant_rps: {
      executor: "constant-arrival-rate",
      rate: 10,          // requests per second to submit
      timeUnit: "1s",
      duration: "1m",
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    failures: ["rate<0.1"],
  },
};

const BASE_URL = "http://103.173.99.217:8000";

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
  headers: { "Content-Type": "application/json" },
  timeout: "10s",   // just for the submit call — it should return immediately
};

export default function () {
  const submitStart = Date.now();

  // 1. Submit — expect 202 immediately
  const submitRes = http.post(`${BASE_URL}/execute`, payload, params);

  const submitted = check(submitRes, {
    "submit status 202": (r) => r.status === 202,
    "got job_id": (r) => {
      try { return !!JSON.parse(r.body).job_id; } catch { return false; }
    },
  });

  if (!submitted) {
    failureRate.add(1);
    return;
  }

  const jobId = JSON.parse(submitRes.body).job_id;

  // 2. Poll until done (max 120 s, poll every 500 ms)
  const pollParams = { timeout: "5s" };
  let verdict = null;

  for (let i = 0; i < 240; i++) {
    sleep(0.5);
    const r = http.get(`${BASE_URL}/result/${jobId}`, pollParams);

    if (r.status !== 200) continue;

    let body;
    try { body = JSON.parse(r.body); } catch { continue; }

    if (body.status === "done") {
      verdict = body.result?.verdict;
      break;
    }
  }

  const elapsed = Date.now() - submitStart;
  e2eLatency.add(elapsed);

  const success = check({ verdict }, {
    "verdict is accepted": (v) => v.verdict === "accepted",
  });

  failureRate.add(!success);
}
