import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    constant_load: {
      executor: "constant-vus",
      vus: 200,
      duration: "60s", // run for 1 minute
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% under 2s
    http_req_failed: ["rate<0.01"], // <1% failures
  },
};

const url = "http://localhost:8000/execute";

const payload = JSON.stringify({
  language: "js",
  source_code:
    "function reverseList(head) { let prev=null; while(head){let next=head.next; head.next=prev; prev=head; head=next;} return prev; }",
  function_name: "reverseList",
  test_cases: [
    {
      input: { head: [1, 2, 3] },
      expected_output: [3, 2, 1],
    },
    {
      input: { head: [1, 2, 3, 4, 5] },
      expected_output: [5, 4, 3, 2, 1],
    },
    {
      input: { head: [10, 20, 30, 40] },
      expected_output: [40, 30, 20, 10],
    },
    {
      input: { head: [5] },
      expected_output: [5],
    },
    {
      input: { head: [] },
      expected_output: [],
    },
    {
      input: { head: [7, 14, 21, 28, 35, 42] },
      expected_output: [42, 35, 28, 21, 14, 7],
    },
    {
      input: { head: [100, 200] },
      expected_output: [200, 100],
    },
    {
      input: { head: [3, 1, 4, 1, 5, 9, 2] },
      expected_output: [2, 9, 5, 1, 4, 1, 3],
    },
    {
      input: { head: [-1, -2, -3, -4] },
      expected_output: [-4, -3, -2, -1],
    },
    {
      input: { head: [0, 1, 0, 1, 0, 1] },
      expected_output: [1, 0, 1, 0, 1, 0],
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

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  sleep(0.2); // small think time to simulate real users
}
