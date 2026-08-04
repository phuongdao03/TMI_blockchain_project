import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    public_search: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 20 },
        { duration: "2m", target: 20 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:search}": ["p(95)<500"],
    "http_req_duration{endpoint:autocomplete}": ["p(95)<250"],
  },
};

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000/api/v1";
const queries = ["son mai", "di san", "my thuat", "van hoa", "ha noi"];

export default function () {
  const query = queries[(__VU + __ITER) % queries.length];
  const search = http.get(
    `${baseUrl}/public/search?q=${encodeURIComponent(query)}&pageSize=20`,
    { tags: { endpoint: "search" } },
  );
  check(search, {
    "search succeeds": (response) => response.status === 200,
    "search does not leak private identifiers": (response) =>
      !response.body.includes("ownerUserId") &&
      !response.body.includes("dossierId"),
  });

  const autocomplete = http.get(
    `${baseUrl}/public/search/autocomplete?q=${encodeURIComponent(query)}`,
    { tags: { endpoint: "autocomplete" } },
  );
  check(autocomplete, {
    "autocomplete succeeds": (response) => response.status === 200,
    "autocomplete does not leak private identifiers": (response) =>
      !response.body.includes("ownerUserId") &&
      !response.body.includes("dossierId"),
  });
  sleep(0.2);
}
