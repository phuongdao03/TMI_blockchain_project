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
  assert.match(pyproject, /requires-python = "==3\.12\.8"/);
  assert.match(pyproject, /\[tool\.mypy\][\s\S]*strict = true/);
  assert.match(pyproject, /\[tool\.ruff\][\s\S]*target-version = "py312"/);
});

test("ignores local secrets and documents local validation", () => {
  const gitignore = readFileSync(".gitignore", "utf8");
  const readme = readFileSync("README.md", "utf8");

  assert.match(gitignore, /^\.env\*$/m);
  assert.match(gitignore, /^!\.env\.example$/m);
  assert.match(gitignore, /^\*\.pem$/m);
  assert.match(readme, /npm ci/);
  assert.match(readme, /npm run lint/);
  assert.match(readme, /npm run typecheck/);
  assert.match(readme, /npm test/);
});
