import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import test from "node:test";

const exec = promisify(execFile);
const probe = fileURLToPath(
  new URL(
    "../infrastructure/scripts/probe-alert-delivery.mjs",
    import.meta.url,
  ),
);
const acknowledgementValidator = fileURLToPath(
  new URL(
    "../infrastructure/scripts/validate-alert-acknowledgement.mjs",
    import.meta.url,
  ),
);

test("alert delivery probe sends a bounded authenticated synthetic event", async () => {
  let received;
  const server = createServer(async (request, response) => {
    let body = "";
    for await (const chunk of request) body += chunk;
    received = {
      authorization: request.headers.authorization,
      body: JSON.parse(body),
    };
    response.writeHead(202, { "Content-Type": "application/json" });
    response.end('{"accepted":true}');
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert.ok(address && typeof address === "object");

  try {
    const result = await exec(process.execPath, [probe], {
      env: {
        ...process.env,
        ALERT_TEST_WEBHOOK_URL: `http://127.0.0.1:${address.port}/alerts`,
        ALERT_TEST_AUTH_TOKEN: "local-test-token",
        ALERT_TEST_ALLOW_HTTP: "1",
      },
    });
    assert.equal(received.authorization, "Bearer local-test-token");
    assert.equal(received.body.name, "operational_readiness_delivery_probe");
    assert.equal(received.body.synthetic, true);
    assert.match(received.body.testId, /^[0-9a-f-]{36}$/);
    assert.doesNotMatch(result.stdout + result.stderr, /local-test-token/);
    assert.match(result.stdout, /"delivered":true/);
  } finally {
    server.close();
  }
});

test("alert delivery probe rejects insecure remote endpoints", async () => {
  await assert.rejects(
    exec(process.execPath, [probe], {
      env: {
        ...process.env,
        ALERT_TEST_WEBHOOK_URL: "http://alerts.example.test/receive",
        ALERT_TEST_AUTH_TOKEN: "must-not-be-printed",
      },
    }),
    (error) => {
      assert.match(error.stderr, /requires HTTPS/);
      assert.doesNotMatch(error.stderr, /must-not-be-printed/);
      return true;
    },
  );
});

test("alert acknowledgement is schema checked and retained with a checksum", async () => {
  const directory = await mkdtemp(join(tmpdir(), "tmi-alert-ack-"));
  const input = join(directory, "input.json");
  const output = join(directory, "evidence");
  const acknowledgement = {
    schemaVersion: 1,
    environment: "staging",
    synthetic: true,
    testId: "b8b7c358-8ad7-4ce5-b622-14eac16ecce8",
    receiverEventId: "receiver-event-481",
    route: "staging-platform-on-call",
    sentAt: "2026-08-12T02:00:00Z",
    receivedAt: "2026-08-12T02:00:02Z",
    acknowledgedAt: "2026-08-12T02:01:00Z",
    owner: "platform-owner",
    status: "ACKNOWLEDGED",
  };
  await writeFile(input, JSON.stringify(acknowledgement));

  const result = await exec(process.execPath, [
    acknowledgementValidator,
    input,
    output,
  ]);
  const retained = JSON.parse(
    await readFile(join(output, "alert-acknowledgement.json"), "utf8"),
  );
  const manifest = await readFile(join(output, "manifest.sha256"), "utf8");

  assert.deepEqual(retained, acknowledgement);
  assert.match(manifest, /^[a-f0-9]{64}  alert-acknowledgement\.json\n$/);
  assert.match(result.stdout, /"retained":true/);

  acknowledgement.acknowledgedAt = "2026-08-12T01:59:00Z";
  await writeFile(input, JSON.stringify(acknowledgement));
  await assert.rejects(
    exec(process.execPath, [
      acknowledgementValidator,
      input,
      join(directory, "bad"),
    ]),
  );
});
