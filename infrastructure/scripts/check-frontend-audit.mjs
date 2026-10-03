import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const ADVISORY = "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm";
const EXPIRES_AT = "2026-10-17T00:00:00Z";
const ALLOWED_VIA = new Map([
  ["braces", ADVISORY],
  ["micromatch", "braces"],
  ["fast-glob", "micromatch"],
  ["@next/eslint-plugin-next", "fast-glob"],
  ["eslint-config-next", "@next/eslint-plugin-next"],
]);

export function checkFrontendAudit(
  report,
  lockfile,
  exitCode,
  now = new Date(),
) {
  if (exitCode !== 0 && exitCode !== 1) {
    throw new Error(`npm audit failed with exit code ${exitCode}`);
  }
  if (
    !report ||
    report.error ||
    !report.vulnerabilities ||
    !report.metadata?.vulnerabilities ||
    !lockfile?.packages
  ) {
    throw new Error("npm audit returned an incomplete report");
  }

  const findings = Object.entries(report.vulnerabilities).filter(
    ([, finding]) => ["high", "critical"].includes(finding.severity),
  );
  const totals = report.metadata.vulnerabilities;
  if (findings.length !== totals.high + totals.critical) {
    throw new Error("npm audit finding count does not match its metadata");
  }
  if (findings.length === 0) {
    if (exitCode !== 0)
      throw new Error("npm audit failed without high findings");
    return false;
  }
  if (exitCode !== 1)
    throw new Error("npm audit reported high findings but exited successfully");
  if (now >= new Date(EXPIRES_AT)) {
    throw new Error(`temporary ${ADVISORY} exception expired on ${EXPIRES_AT}`);
  }

  for (const [name, finding] of findings) {
    const expectedVia = ALLOWED_VIA.get(name);
    if (
      !expectedVia ||
      finding.severity !== "high" ||
      !Array.isArray(finding.via) ||
      finding.via.length !== 1 ||
      (typeof finding.via[0] === "string"
        ? finding.via[0] !== expectedVia
        : finding.via[0]?.url !== expectedVia ||
          finding.via[0]?.name !== name) ||
      !Array.isArray(finding.nodes) ||
      finding.nodes.length === 0 ||
      finding.nodes.some((node) => lockfile.packages[node]?.dev !== true)
    ) {
      throw new Error(`unapproved frontend audit finding: ${name}`);
    }
  }
  if (findings.length !== ALLOWED_VIA.size) {
    throw new Error(
      "frontend audit findings differ from the approved dependency chain",
    );
  }
  return true;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  try {
    const [, , reportPath, exitCode] = process.argv;
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    const lockfile = JSON.parse(
      readFileSync("frontend/package-lock.json", "utf8"),
    );
    const excepted = checkFrontendAudit(report, lockfile, Number(exitCode));
    if (excepted) {
      console.warn(
        `::warning title=Temporary audit exception::${ADVISORY} is allowed for frontend lint dependencies until ${EXPIRES_AT}`,
      );
    }
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
