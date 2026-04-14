import http from "k6/http";
import { check, sleep } from "k6";

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
        { duration: "1m", target: 150 }, // final step adjusted
      ],
      gracefulRampDown: "30s",
    },
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

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
