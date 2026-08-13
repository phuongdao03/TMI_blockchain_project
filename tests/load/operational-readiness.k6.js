import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    operational_readiness: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "2m", target: 10 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:health}": ["p(95)<250"],
    "http_req_duration{endpoint:ready}": ["p(95)<500"],
    "http_req_duration{endpoint:home}": ["p(95)<500"],
    "http_req_duration{endpoint:works}": ["p(95)<750"],
    "http_req_duration{endpoint:verification}": ["p(95)<750"],
  },
};

const baseUrl = (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const environment = __ENV.LOAD_ENVIRONMENT || "local";

export function setup() {
  const certificateNumber = __ENV.VERIFY_CERTIFICATE_NUMBER;
  if (!certificateNumber || !/^[A-Za-z0-9-]{3,128}$/.test(certificateNumber)) {
    throw new Error(
      "VERIFY_CERTIFICATE_NUMBER must identify a safe seeded certificate",
    );
  }
  if (environment !== "local") {
    if (
      environment !== "staging" ||
      !baseUrl.startsWith("https://") ||
      __ENV.STAGING_READINESS_APPROVED !== "1"
    ) {
      throw new Error("staging load requires HTTPS and explicit approval");
    }
  }
  return { certificateNumber };
}

const safeBody = (response) => response.body || "";
const noPrivateData = (response) =>
  !safeBody(response).includes("ownerUserId") &&
  !safeBody(response).includes("dossierId") &&
  !safeBody(response).includes("privateKey");

export default function ({ certificateNumber }) {
  const requests = [
    ["health", `${baseUrl}/health`],
    ["ready", `${baseUrl}/ready`],
    ["home", `${baseUrl}/api/v1/public/home`],
    ["works", `${baseUrl}/api/v1/public/works?pageSize=20`],
    [
      "verification",
      `${baseUrl}/api/v1/verify/certificate/${encodeURIComponent(certificateNumber)}`,
    ],
  ];

  for (const [endpoint, url] of requests) {
    const response = http.get(url, { tags: { endpoint } });
    check(response, {
      [`${endpoint} succeeds`]: (result) => result.status === 200,
      [`${endpoint} does not leak private data`]: noPrivateData,
    });
  }
  sleep(0.2);
}
