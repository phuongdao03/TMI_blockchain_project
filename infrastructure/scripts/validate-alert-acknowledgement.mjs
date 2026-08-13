import { createHash } from "node:crypto";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

if (process.argv.length !== 4) {
  console.error(
    "usage: validate-alert-acknowledgement.mjs <input.json> <output-directory>",
  );
  process.exit(64);
}

const input = resolve(process.argv[2]);
const output = resolve(process.argv[3]);
let inputSize;
try {
  inputSize = (await stat(input)).size;
} catch {
  console.error("alert acknowledgement input is unavailable");
  process.exit(65);
}
if (inputSize > 16_384) {
  console.error("alert acknowledgement exceeds the size limit");
  process.exit(65);
}

let value;
try {
  value = JSON.parse(await readFile(input, "utf8"));
} catch {
  console.error("alert acknowledgement must be valid JSON");
  process.exit(65);
}

const expectedKeys = [
  "schemaVersion",
  "environment",
  "synthetic",
  "testId",
  "receiverEventId",
  "route",
  "sentAt",
  "receivedAt",
  "acknowledgedAt",
  "owner",
  "status",
];
const exactKeys =
  value &&
  typeof value === "object" &&
  !Array.isArray(value) &&
  JSON.stringify(Object.keys(value).sort()) ===
    JSON.stringify([...expectedKeys].sort());
const boundedIdentifier = (candidate) =>
  typeof candidate === "string" &&
  /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(candidate);
const timestamp = (candidate) =>
  typeof candidate === "string" &&
  candidate.length <= 64 &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(candidate) &&
  Number.isFinite(Date.parse(candidate));
const sentAt = Date.parse(value?.sentAt);
const receivedAt = Date.parse(value?.receivedAt);
const acknowledgedAt = Date.parse(value?.acknowledgedAt);

if (
  !exactKeys ||
  value.schemaVersion !== 1 ||
  value.environment !== "staging" ||
  value.synthetic !== true ||
  !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value.testId,
  ) ||
  !boundedIdentifier(value.receiverEventId) ||
  !boundedIdentifier(value.route) ||
  !boundedIdentifier(value.owner) ||
  !timestamp(value.sentAt) ||
  !timestamp(value.receivedAt) ||
  !timestamp(value.acknowledgedAt) ||
  receivedAt < sentAt ||
  acknowledgedAt < receivedAt ||
  value.status !== "ACKNOWLEDGED"
) {
  console.error("alert acknowledgement does not match the approved schema");
  process.exit(65);
}

const serialized = `${JSON.stringify(value, null, 2)}\n`;
const digest = createHash("sha256").update(serialized).digest("hex");
try {
  await mkdir(output, { recursive: true });
  await writeFile(join(output, "alert-acknowledgement.json"), serialized, {
    flag: "wx",
  });
  await writeFile(
    join(output, "manifest.sha256"),
    `${digest}  alert-acknowledgement.json\n`,
    { flag: "wx" },
  );
} catch {
  console.error("alert acknowledgement evidence could not be retained");
  process.exit(73);
}
process.stdout.write(`${JSON.stringify({ retained: true, sha256: digest })}\n`);
