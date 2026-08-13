import { readFile, stat } from "node:fs/promises";

const exactKeys = (value, expected) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  return (
    JSON.stringify(Object.keys(value).sort()) ===
    JSON.stringify([...expected].sort())
  );
};

const bounded = (value, max = 128) =>
  typeof value === "string" && value.length > 0 && value.length <= max;
const minutes = (value) => Number.isInteger(value) && value >= 0;
const timestamp = (value) =>
  bounded(value) && Number.isFinite(Date.parse(value));

export async function readAndValidateEvidence(path) {
  if ((await stat(path)).size > 32_768) {
    throw new Error("readiness evidence exceeds the size limit");
  }
  const raw = await readFile(path);
  let value;
  try {
    value = JSON.parse(raw.toString("utf8"));
  } catch {
    throw new Error("readiness evidence must be valid JSON");
  }
  if (
    !exactKeys(value, [
      "schemaVersion",
      "drillType",
      "environment",
      "startedAt",
      "finishedAt",
      "targets",
      "achieved",
      "source",
      "checks",
      "approvals",
      "status",
    ]) ||
    value.schemaVersion !== 1 ||
    !["postgres_restore", "redis_loss", "application_rollback"].includes(
      value.drillType,
    ) ||
    value.environment !== "staging" ||
    !timestamp(value.startedAt) ||
    !timestamp(value.finishedAt) ||
    Date.parse(value.finishedAt) <= Date.parse(value.startedAt) ||
    !exactKeys(value.targets, ["rpoMinutes", "rtoMinutes"]) ||
    !minutes(value.targets.rpoMinutes) ||
    !minutes(value.targets.rtoMinutes) ||
    !exactKeys(value.achieved, ["rpoMinutes", "rtoMinutes"]) ||
    !minutes(value.achieved.rpoMinutes) ||
    !minutes(value.achieved.rtoMinutes) ||
    !exactKeys(value.source, [
      "backupId",
      "manifestSha256",
      "migrationRevision",
      "imageTag",
    ]) ||
    !bounded(value.source.backupId) ||
    !/^[a-f0-9]{64}$/i.test(value.source.manifestSha256) ||
    !bounded(value.source.migrationRevision) ||
    !bounded(value.source.imageTag) ||
    !exactKeys(value.checks, [
      "checksumVerified",
      "smokeTestsPassed",
      "duplicateSideEffectsDetected",
    ]) ||
    typeof value.checks.checksumVerified !== "boolean" ||
    typeof value.checks.smokeTestsPassed !== "boolean" ||
    typeof value.checks.duplicateSideEffectsDetected !== "boolean" ||
    !exactKeys(value.approvals, ["owner", "independentVerifier"]) ||
    !bounded(value.approvals.owner) ||
    !bounded(value.approvals.independentVerifier) ||
    !["PASS", "FAIL"].includes(value.status)
  ) {
    throw new Error("readiness evidence does not match the approved schema");
  }
  if (
    value.status === "PASS" &&
    (!value.checks.checksumVerified ||
      !value.checks.smokeTestsPassed ||
      value.checks.duplicateSideEffectsDetected ||
      value.achieved.rpoMinutes > value.targets.rpoMinutes ||
      value.achieved.rtoMinutes > value.targets.rtoMinutes)
  ) {
    throw new Error("passing evidence does not satisfy recovery gates");
  }
  return { raw, value };
}
