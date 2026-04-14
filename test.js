import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------
const failureRate    = new Rate("failures");
const e2eLatency     = new Trend("e2e_latency_ms",    true); // submit → verdict
const submitLatency  = new Trend("submit_latency_ms", true); // just the POST /execute
const pollCount      = new Trend("poll_count");              // how many polls per job
const jobsTimedOut   = new Counter("jobs_timed_out");        // jobs that never finished in time
const jobsExpired    = new Counter("jobs_expired");          // jobs the server marked expired

// ---------------------------------------------------------------------------
// Scenario
// 50 RPS for 5 minutes = 15,000 jobs submitted.
// gracefulStop = 2 min: VUs already mid-poll get 2 extra minutes to finish.
//
// VU sizing: at 50 RPS with ~15–30 s avg e2e time, up to 50×30 = 1500 VUs
// may be active simultaneously.  preAllocatedVUs starts a baseline pool;
// k6 auto-scales up to maxVUs as needed.
// ---------------------------------------------------------------------------
export const options = {
  scenarios: {
    constant_rps: {
      executor:        "constant-arrival-rate",
      rate:            50,          // iterations per second
      timeUnit:        "1s",
      duration:        "5m",        // submit phase
      preAllocatedVUs: 800,
      maxVUs:          2500,
      gracefulStop:    "2m",        // headroom for in-flight polls to finish
    },
  },
  thresholds: {
    // Overall job failure rate must stay below 5 %
    failures: ["rate<0.05"],

    // 90 % of jobs should complete within 60 s end-to-end
    e2e_latency_ms: ["p(90)<60000"],

    // 99 % within 120 s (the full graceful-stop budget)
    "e2e_latency_ms{p:99}": ["p(99)<120000"],

    // The submit call itself should be fast (queue-enqueue only)
    submit_latency_ms: ["p(95)<1000"],
  },
};

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const BASE_URL     = "http://103.173.99.217:8000";
const POLL_INTERVAL_MS = 500;          // poll every 500 ms
const MAX_POLL_SECONDS = 110;          // give up after this many seconds of polling
                                       // (keeps well inside the 2-min gracefulStop)
const MAX_POLLS    = Math.floor((MAX_POLL_SECONDS * 1000) / POLL_INTERVAL_MS);

const SUBMIT_PARAMS = {
  headers: { "Content-Type": "application/json" },
  timeout: "10s",   // submit must be fast; fail fast if API is down
};

const POLL_PARAMS = {
  timeout: "5s",
};

const PAYLOAD = JSON.stringify({
  language: "cpp",
  source_code:
    "bool hasCycle(ListNode* head) { ListNode *slow=head,*fast=head; " +
    "while(fast && fast->next){ slow=slow->next; fast=fast->next->next; " +
    "if(slow==fast) return true;} return false; }",
  function_name: "hasCycle",
  test_cases: [
    { input: { head: [1, 2, 3, 4] }, expected_output: false },
  ],
});

// ---------------------------------------------------------------------------
// VU entrypoint
// ---------------------------------------------------------------------------
export default function () {
  const wallStart = Date.now();

  // ------------------------------------------------------------------
  // 1. Submit
  // ------------------------------------------------------------------
  const submitRes = http.post(`${BASE_URL}/execute`, PAYLOAD, SUBMIT_PARAMS);
  submitLatency.add(Date.now() - wallStart);

  const submitOk = check(submitRes, {
    "submit → 202": (r) => r.status === 202,
  });

  if (!submitOk) {
    // API returned non-202 (could be 503 queue-full or a real error)
    failureRate.add(1);
    return;
  }

  let jobId;
  try {
    jobId = JSON.parse(submitRes.body).job_id;
  } catch (_) {
    failureRate.add(1);
    return;
  }

  if (!jobId) {
    failureRate.add(1);
    return;
  }

  // ------------------------------------------------------------------
  // 2. Poll until done
  // ------------------------------------------------------------------
  let polls   = 0;
  let verdict = null;
  let timedOut = true;

  for (let i = 0; i < MAX_POLLS; i++) {
    sleep(POLL_INTERVAL_MS / 1000);
    polls++;

    const r = http.get(`${BASE_URL}/result/${jobId}`, POLL_PARAMS);

    if (r.status !== 200) continue;

    let body;
    try { body = JSON.parse(r.body); } catch (_) { continue; }

    if (body.status === "done") {
      verdict  = body.result?.verdict ?? null;
      timedOut = false;

      // Track server-side job expiry separately
      if (verdict === "error" &&
          (body.result?.error_message ?? "").includes("expired")) {
        jobsExpired.add(1);
      }
      break;
    }
  }

  pollCount.add(polls);
  e2eLatency.add(Date.now() - wallStart);

  if (timedOut) {
    jobsTimedOut.add(1);
    failureRate.add(1);
    return;
  }

  // ------------------------------------------------------------------
  // 3. Validate verdict
  // ------------------------------------------------------------------
  const success = check({ verdict }, {
    "verdict accepted": (v) => v.verdict === "accepted",
  });

  failureRate.add(!success);
}
