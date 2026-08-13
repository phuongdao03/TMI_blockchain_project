import { randomUUID } from "node:crypto";

const endpoint = process.env.ALERT_TEST_WEBHOOK_URL;
const token = process.env.ALERT_TEST_AUTH_TOKEN;
if (!endpoint || !token || token.length > 4096) {
  console.error("alert delivery probe configuration is invalid");
  process.exit(64);
}

let url;
try {
  url = new URL(endpoint);
} catch {
  console.error("alert delivery probe endpoint is invalid");
  process.exit(64);
}
const localHttp =
  url.protocol === "http:" &&
  ["127.0.0.1", "localhost"].includes(url.hostname) &&
  process.env.ALERT_TEST_ALLOW_HTTP === "1";
if (url.protocol !== "https:" && !localHttp) {
  console.error("alert delivery probe requires HTTPS");
  process.exit(64);
}

const testId = randomUUID();
const payload = {
  schemaVersion: 1,
  name: "operational_readiness_delivery_probe",
  severity: "ticket",
  source: "tmi-staging",
  synthetic: true,
  testId,
  occurredAt: new Date().toISOString(),
};

try {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    redirect: "error",
    signal: AbortSignal.timeout(5_000),
  });
  await response.body?.cancel();
  if (!response.ok) throw new Error("receiver rejected the synthetic alert");
  process.stdout.write(
    `${JSON.stringify({ delivered: true, testId, statusCode: response.status })}\n`,
  );
} catch (error) {
  console.error(
    error instanceof Error ? error.message : "alert delivery probe failed",
  );
  process.exit(1);
}
