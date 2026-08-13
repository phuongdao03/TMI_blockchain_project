import assert from "node:assert/strict";
import { readFileSync, statSync } from "node:fs";
import test from "node:test";

/** @param {string} path */
const readJson = (path) => JSON.parse(readFileSync(path, "utf8"));

test("defines the required monorepo roots", () => {
  for (const directory of [
    "frontend",
    "backend",
    "contracts",
    "infrastructure",
  ]) {
    assert.equal(statSync(directory).isDirectory(), true);
  }
});

test("pins the root JavaScript toolchain and exposes quality scripts", () => {
  const packageJson = readJson("package.json");

  assert.equal(packageJson.engines.node, "24.18.0");
  assert.equal(packageJson.packageManager, "npm@11.16.0");
  assert.equal(packageJson.devDependencies.prettier, "3.6.2");
  assert.equal(packageJson.devDependencies.typescript, "5.9.3");

  for (const script of ["format", "lint", "typecheck", "test"]) {
    assert.equal(typeof packageJson.scripts[script], "string");
  }
  assert.equal(
    packageJson.scripts.test,
    "npm run test:root && npm run test:frontend && npm run test:backend",
  );
  assert.equal(
    packageJson.scripts["test:root"],
    "node --test tests/repository-structure.test.mjs",
  );
});

test("enables strict checks for TypeScript and Python", () => {
  const tsconfig = readJson("frontend/tsconfig.json");
  const pyproject = readFileSync("backend/pyproject.toml", "utf8");

  assert.equal(tsconfig.compilerOptions.strict, true);
  assert.equal(tsconfig.compilerOptions.noEmit, true);
  assert.match(pyproject, /requires-python = "==3\.12\.13"/);
  assert.match(pyproject, /\[tool\.mypy\][\s\S]*strict = true/);
  assert.match(pyproject, /\[tool\.ruff\][\s\S]*target-version = "py312"/);
});

test("ignores local secrets and documents local validation", () => {
  const gitignore = readFileSync(".gitignore", "utf8");
  const readme = readFileSync("README.md", "utf8");

  assert.match(gitignore, /^\.env\*$/m);
  assert.match(gitignore, /^!\.env\.example$/m);
  assert.match(gitignore, /^!infrastructure\/\.env\.staging\.example$/m);
  assert.match(gitignore, /^\*\.pem$/m);
  assert.match(gitignore, /^client_secret_\*\.json$/m);
  assert.match(gitignore, /^firebase-service-account\*\.json$/m);
  assert.match(gitignore, /^\*firebase-adminsdk\*\.json$/m);
  assert.match(gitignore, /^service-account\*\.json$/m);
  assert.match(readme, /npm ci/);
  assert.match(readme, /npm run lint/);
  assert.match(readme, /npm run typecheck/);
  assert.match(readme, /npm test/);
});

test("pins a redacted full-history secret scan with a synthetic canary", () => {
  const workflow = readFileSync(".github/workflows/delivery.yml", "utf8");
  const scanner = readFileSync(
    "infrastructure/scripts/verify-gitleaks.sh",
    "utf8",
  );
  const config = readFileSync(".gitleaks.toml", "utf8");

  assert.match(workflow, /name: Secret scan/);
  assert.match(workflow, /fetch-depth: 0/);
  assert.match(workflow, /infrastructure\/scripts\/verify-gitleaks\.sh/);
  assert.match(scanner, /ghcr\.io\/gitleaks\/gitleaks:v8\.30\.1/);
  assert.match(scanner, /gitleaks[^\n]*git|\"\$\{scanner_image\}\" git/);
  assert.match(scanner, /--redact/);
  assert.match(scanner, /synthetic canary/i);
  assert.match(scanner, /\[\[ -f "\$\{repository_root\}\/\$\{path\}" \]\]/);
  assert.match(scanner, /MSYS_NO_PATHCONV=1 docker run/);
  assert.match(scanner, /cygpath -w/);
  assert.match(config, /useDefault\s*=\s*true/);
  assert.match(config, /google-oauth-client-secret-json/);
});
