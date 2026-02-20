import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 20,
  duration: "60s",
};

const payload = JSON.stringify({
  language: "java",
  source_code:
    "class Solution { public int[] twoSum(int[] nums, int target) { HashMap<Integer,Integer> map = new HashMap<>(); for (int i =0;i<nums.length;i++) { int x = target - nums[i]; if(map.containsKey(x)){ return new int[] {map.get(x),i}; } map.put(nums[i],i); } return new int[] {}; } }",
  function_name: "twoSum",
  test_cases: [
    {
      input: {
        nums: [2, 7, 11, 15],
        target: 9,
      },
      expected_output: [0, 1],
    },
    {
      input: {
        nums: [3, 2, 4],
        target: 6,
      },
      expected_output: [1, 2],
    },
    {
      input: {
        nums: [3, 3],
        target: 6,
      },
      expected_output: [0, 1],
    },
  ],
});

const params = {
  headers: {
    "Content-Type": "application/json",
  },
};

export default function () {
  const res = http.post("http://localhost:8000/execute", payload, params);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
