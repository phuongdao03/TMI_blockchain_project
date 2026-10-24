import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export function checkFrontendAudit(report, exitCode) {
  if (exitCode !== 0 && exitCode !== 1) {
    throw new Error(`npm audit failed with exit code ${exitCode}`);
  }
  if (
    !report ||
    report.error ||
    !report.vulnerabilities ||
    !report.metadata?.vulnerabilities
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
  throw new Error(
    `frontend audit found high or critical vulnerabilities: ${findings
      .map(([name]) => name)
      .join(", ")}`,
  );
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  try {
    const [, , reportPath, exitCode] = process.argv;
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    checkFrontendAudit(report, Number(exitCode));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
