import assert from "node:assert/strict";
import test from "node:test";

import { checkFrontendAudit } from "../infrastructure/scripts/check-frontend-audit.mjs";

const chain = [
  [
    "braces",
    {
      name: "braces",
      url: "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
    },
  ],
  ["micromatch", "braces"],
  ["fast-glob", "micromatch"],
  ["@next/eslint-plugin-next", "fast-glob"],
  ["eslint-config-next", "@next/eslint-plugin-next"],
];

function fixture() {
  const vulnerabilities = {};
  const packages = {};
  for (const [name, via] of chain) {
    const node = `node_modules/${name}`;
    vulnerabilities[name] = { severity: "high", via: [via], nodes: [node] };
    packages[node] = { dev: true };
  }
  return {
    report: {
      vulnerabilities,
      metadata: { vulnerabilities: { high: 5, critical: 0 } },
    },
    lockfile: { packages },
  };
}

const validDate = new Date("2026-10-03T00:00:00Z");

test("accepts only the approved development dependency chain before expiry", () => {
  const { report, lockfile } = fixture();
  assert.equal(checkFrontendAudit(report, lockfile, 1, validDate), true);
});

test("passes a clean audit after the exception expires", () => {
  const { report, lockfile } = fixture();
  report.vulnerabilities = {};
  report.metadata.vulnerabilities.high = 0;
  assert.equal(
    checkFrontendAudit(report, lockfile, 0, new Date("2026-10-18T00:00:00Z")),
    false,
  );
});

test("rejects another advisory, production dependency, and expired exception", () => {
  const { report, lockfile } = fixture();
  report.vulnerabilities.braces.via[0].url =
    "https://github.com/advisories/other";
  assert.throws(() => checkFrontendAudit(report, lockfile, 1, validDate));

  report.vulnerabilities.braces.via[0].url = chain[0][1].url;
  lockfile.packages["node_modules/braces"].dev = false;
  assert.throws(() => checkFrontendAudit(report, lockfile, 1, validDate));

  lockfile.packages["node_modules/braces"].dev = true;
  assert.throws(() =>
    checkFrontendAudit(report, lockfile, 1, new Date("2026-10-17T00:00:00Z")),
  );
});

test("rejects incomplete or failed audit responses", () => {
  const { report, lockfile } = fixture();
  assert.throws(() =>
    checkFrontendAudit(
      { error: { message: "registry unavailable" } },
      lockfile,
      1,
    ),
  );
  assert.throws(() => checkFrontendAudit(report, lockfile, 2, validDate));
  report.vulnerabilities["unexpected-package"] = {
    severity: "high",
    via: ["other"],
    nodes: ["node_modules/unexpected-package"],
  };
  report.metadata.vulnerabilities.high = 6;
  assert.throws(() => checkFrontendAudit(report, lockfile, 1, validDate));
});
