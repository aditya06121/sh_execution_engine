import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    constant_load: {
      executor: "constant-vus",
      vus: 10,
      duration: "1m",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<5000"], // 5s for TS (compile heavy)
    http_req_failed: ["rate<0.01"],
  },
};

const payload = JSON.stringify({
  language: "ts",
  source_code:
    "function sumArray(nums: number[]): number { let sum = 0; for (let i = 0; i < nums.length; i++) { sum += nums[i]; } return sum; }",
  function_name: "sumArray",
  test_cases: [
    { input: { nums: [1] }, expected_output: 1 },
    { input: { nums: [1, 2] }, expected_output: 3 },
    { input: { nums: [1, 2, 3] }, expected_output: 6 },
    { input: { nums: [1, 2, 3, 4] }, expected_output: 10 },
    { input: { nums: [1, 2, 3, 4, 5] }, expected_output: 15 },
    { input: { nums: [10, 20, 30] }, expected_output: 60 },
    { input: { nums: [5, 5, 5, 5] }, expected_output: 20 },
    { input: { nums: [100] }, expected_output: 100 },
    { input: { nums: [0, 0, 0] }, expected_output: 0 },
    { input: { nums: [7, 8, 9] }, expected_output: 24 },
    { input: { nums: [2, 4, 6, 8, 10] }, expected_output: 30 },
    { input: { nums: [3, 3, 3, 3, 3, 3] }, expected_output: 18 },
    { input: { nums: [50, 50] }, expected_output: 100 },
  ],
});

export default function () {
  const res = http.post("http://localhost:8000/execute", payload, {
    headers: { "Content-Type": "application/json" },
  });

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response < 5s": (r) => r.timings.duration < 5000,
  });
}
