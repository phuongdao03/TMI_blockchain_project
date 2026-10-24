import assert from "node:assert/strict";
import test from "node:test";

import { checkFrontendAudit } from "../infrastructure/scripts/check-frontend-audit.mjs";

function fixture(vulnerabilities = {}, counts = { high: 0, critical: 0 }) {
  return {
    report: {
      vulnerabilities,
      metadata: { vulnerabilities: counts },
    },
  };
}

test("passes a clean audit", () => {
  const { report } = fixture();
  assert.equal(checkFrontendAudit(report, 0), false);
});

test("rejects every high or critical finding", () => {
  const { report } = fixture(
    {
      vulnerable: { severity: "high" },
      critical: { severity: "critical" },
    },
    { high: 1, critical: 1 },
  );
  assert.throws(() => checkFrontendAudit(report, 1), /vulnerable, critical/);
});

test("rejects incomplete or failed audit responses", () => {
  const { report } = fixture();
  assert.throws(() =>
    checkFrontendAudit({ error: { message: "registry unavailable" } }, 1),
  );
  assert.throws(() => checkFrontendAudit(report, 2));
  assert.throws(() => checkFrontendAudit(report, 1));
  report.vulnerabilities["unexpected-package"] = {
    severity: "high",
  };
  report.metadata.vulnerabilities.high = 1;
  assert.throws(() => checkFrontendAudit(report, 0));
});
