import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import test from "node:test";

/** @param {string} path */
const readJson = (path) => JSON.parse(readFileSync(path, "utf8"));

/** @param {string} root */
const sourceFiles = (root) =>
  readdirSync(root, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => `${entry.parentPath}/${entry.name}`.replaceAll("\\", "/"))
    .filter((path) => /\.(py|ts|tsx)$/.test(path));

const approvedRootEntries = new Set([
  ".editorconfig",
  ".env.example",
  ".firebaserc.example",
  ".gitattributes",
  ".github",
  ".gitignore",
  ".gitleaks.toml",
  ".node-version",
  ".npmrc",
  ".nvmrc",
  ".prettierignore",
  ".prettierrc.json",
  ".python-version",
  "AGENTS.md",
  "README.md",
  "SECURITY.md",
  "backend",
  "compose.yaml",
  "contracts",
  "docs",
  "frontend",
  "infrastructure",
  "package-lock.json",
  "package.json",
  "tests",
  "vercel.json",
]);
const generatedDirectoryNames = new Set([
  "__pycache__",
  ".mypy_cache",
  ".next",
  ".pytest_cache",
  ".ruff_cache",
  "coverage",
  "node_modules",
  "playwright-report",
  "test-results",
]);
const isGeneratedDirectoryName = (segment) =>
  generatedDirectoryNames.has(segment) ||
  /^\.next(?:[-_]|$)/i.test(segment) ||
  /^\.pytest(?:[-_]|$)/i.test(segment) ||
  /^\.mypy(?:[-_]|$)/i.test(segment) ||
  /^\.ruff(?:[-_]|$)/i.test(segment) ||
  /^\.tmp(?:[-_]|$)/i.test(segment) ||
  segment === ".runtime";
const largeFileReviewLimit = 25 * 1024 * 1024;
const largeFileAllowlist = new Set([
  // Retained as source media; this file is not copied into the frontend image.
  "docs/design/source-assets/tinh-hoa-viet-15-year-intro.mp4",
]);
const validAmbiguousFilenameAllowlist = new Set([
  "infrastructure/scripts/validate-backup.sh",
]);

/** @returns {string[]} */
const repositoryPaths = () =>
  execFileSync(
    "git",
    ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    { encoding: "utf8" },
  )
    .split("\0")
    .filter((path) => path && existsSync(path))
    .map((path) => path.replaceAll("\\", "/"));

/** @param {string[]} paths */
const repositoryHygieneViolations = (paths) =>
  paths.flatMap((path) => {
    const segments = path.split("/");
    const filename = segments.at(-1) ?? path;
    const stem = filename.replace(/\.[^.]+$/, "");
    const violations = [];

    if (
      segments.length === 1 &&
      /\.(avif|gif|jpe?g|png|svg|webp|mp4|mov|webm|woff2?|ttf|otf|eot)$/i.test(
        filename,
      )
    ) {
      violations.push(`${path}: runtime or design asset at repository root`);
    }
    if (!approvedRootEntries.has(segments[0])) {
      violations.push(`${path}: root entry ${segments[0]} is not allowlisted`);
    }
    if (segments.some(isGeneratedDirectoryName)) {
      violations.push(`${path}: generated output or cache is tracked`);
    }
    if (/^ChatGPT Image\s/i.test(filename)) {
      violations.push(`${path}: default image-generator filename`);
    }
    if (
      !validAmbiguousFilenameAllowlist.has(path) &&
      /(?:^|[-_. ])(?:final|copy|backup|temp|tmp)\d*$/i.test(stem)
    ) {
      violations.push(`${path}: temporary or ambiguous filename suffix`);
    }
    if (/\.(log|pyc|pyo)$/i.test(filename)) {
      violations.push(`${path}: generated log or bytecode file`);
    }

    return violations;
  });

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

test("production runtime is THVProofRegistry-only", () => {
  const archivedBackend = new Set(
    [
      "dependencies.py",
      "gateway.py",
      "human_signing_dependencies.py",
      "human_signing_service.py",
      "service.py",
    ].map((name) => `backend/app/modules/blockchain/${name}`),
  );
  archivedBackend.add("backend/app/workers/blockchain_tasks.py");

  const activeBackend = sourceFiles("backend/app")
    .filter((path) => !path.startsWith("backend/app/tests/"))
    .filter((path) => !path.startsWith("backend/app/migrations/"))
    .filter((path) => !archivedBackend.has(path));
  const activeFrontend = sourceFiles("frontend/src").filter(
    (path) => !/\.test\.(ts|tsx)$/.test(path),
  );
  const forbiddenRequestTokens = [
    /modules\.blockchain\.(gateway|service|dependencies|human_signing_service|human_signing_dependencies)/,
    /app\.workers\.blockchain_tasks/,
    /\bissueCertificate\b/,
    /\brevokeCertificate\b/,
    /\brecordDocumentEvidence\b/,
    /\bverifyDocumentEvidence\b/,
  ];

  for (const path of [...activeBackend, ...activeFrontend]) {
    const source = readFileSync(path, "utf8");
    for (const token of forbiddenRequestTokens) {
      assert.doesNotMatch(
        source,
        token,
        `${path} contains legacy runtime flow`,
      );
    }
  }

  const productionEnvironment = readFileSync(
    "infrastructure/.env.production.example",
    "utf8",
  );
  assert.doesNotMatch(productionEnvironment, /^CERTIFICATE_CONTRACT_ADDRESS=/m);
  assert.doesNotMatch(productionEnvironment, /^BLOCKCHAIN_CONTRACT_ABI_PATH=/m);
  assert.match(
    productionEnvironment,
    /^THV_PROOF_REGISTRY_CONTRACT_ADDRESS=0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F$/m,
  );

  const pyproject = readFileSync("backend/pyproject.toml", "utf8");
  for (const path of archivedBackend) {
    assert.match(pyproject, new RegExp(path.replace(/^backend\//, "")));
  }

  for (const path of [
    ".github/workflows/contract-release.yml",
    "infrastructure/scripts/run-document-proof-production-gate.mjs",
  ]) {
    const productionGate = readFileSync(path, "utf8");
    assert.doesNotMatch(
      productionGate,
      /CertificateRegistry|test:provenance|smoke-anvil/,
      `${path} builds or exercises the archived registry`,
    );
  }
});

test("repository hygiene reports root clutter and generated artifacts", () => {
  const paths = [
    "logo.png",
    "animation-plans/scroll.md",
    "docs/ChatGPT Image Source.png",
    "frontend/test-results/.last-run.json",
    "frontend/.next-community-preview/cache.js",
    "src/banner-final2.svg",
    "backend/tmp/worker.log",
  ];
  const violations = repositoryHygieneViolations(paths);

  for (const path of paths) {
    assert.ok(violations.some((violation) => violation.startsWith(`${path}:`)));
  }
  assert.deepEqual(
    repositoryHygieneViolations(["infrastructure/scripts/validate-backup.sh"]),
    [],
  );
});

test("tracked and unignored repository files satisfy hygiene rules", () => {
  const paths = repositoryPaths();
  const violations = repositoryHygieneViolations(paths);
  const unreviewedLargeFiles = paths.filter(
    (path) =>
      statSync(path).size > largeFileReviewLimit &&
      !largeFileAllowlist.has(path),
  );
  const missingLargeFileReviews = [...largeFileAllowlist].filter(
    (path) => !paths.includes(path),
  );

  assert.deepEqual(violations, [], violations.join("\n"));
  assert.deepEqual(unreviewedLargeFiles, [], unreviewedLargeFiles.join("\n"));
  assert.deepEqual(missingLargeFileReviews, []);
});

test("Delivery runs the root repository checks on pull requests", () => {
  const workflow = readFileSync(".github/workflows/delivery.yml", "utf8");

  assert.match(workflow, /^  pull_request:/m);
  assert.match(workflow, /node --test tests\/\*\.test\.mjs/);
});

test("canonical runtime brand, voucher, rank, and PDF assets remain present", () => {
  for (const path of [
    "frontend/public/assets/brand/chim-lac.jpg",
    "frontend/public/assets/brand/logo-tinh-hoa-viet.png",
    "frontend/public/assets/brand/trong-dong.png",
    "frontend/public/images/promotions/golden-voucher.png",
    "frontend/public/assets/membership/pricing/bronze.png",
    "frontend/public/assets/membership/pricing/silver.png",
    "frontend/public/assets/membership/pricing/gold.png",
    "frontend/public/assets/membership/pricing/diamond.png",
    "frontend/public/assets/membership/avatar-frames/bronze.png",
    "frontend/public/assets/membership/avatar-frames/silver.png",
    "frontend/public/assets/membership/avatar-frames/gold.png",
    "frontend/public/assets/membership/avatar-frames/diamond.png",
    "backend/app/assets/images/logo-tinh-hoa-viet.png",
    "backend/app/assets/images/trong-dong.png",
  ]) {
    assert.equal(existsSync(path), true, `${path} must remain available`);
  }
});
