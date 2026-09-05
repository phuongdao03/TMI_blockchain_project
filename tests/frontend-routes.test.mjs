import assert from "node:assert/strict";
import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const appRoot = "frontend/src/app";
const sourceRoot = "frontend/src";

const routeMigrations = [
  ["(public)/quy-trinh", "(public)/process"],
  ["(public)/chinh-sach", "(public)/policies"],
  ["(public)/thu-vien", "(public)/works"],
  ["(public)/tai-san", "(public)/works"],
  ["(public)/ban-do", "(public)/map"],
  ["(public)/kiem-tra", "(public)/verify"],
  ["(public)/binh-chon", "(public)/voting"],
  ["(public)/tim-kiem", "(public)/search"],
  ["(dashboard)/ho-so", "(dashboard)/dossiers"],
  ["(dashboard)/tham-dinh", "(dashboard)/reviews"],
  ["(dashboard)/chung-thu", "(dashboard)/certificates"],
  ["(dashboard)/thanh-toan", "(dashboard)/payments"],
  ["(dashboard)/thong-bao", "(dashboard)/notifications"],
  ["(dashboard)/tai-khoan", "(dashboard)/account"],
  ["(dashboard)/lich-su-binh-chon", "(dashboard)/vote-history"],
  ["(dashboard)/lich-su-hoat-dong", "(dashboard)/activity"],
  ["(dashboard)/admin/bao-cao", "(dashboard)/admin/reports"],
  ["(dashboard)/admin/binh-chon", "(dashboard)/admin/voting"],
  ["(dashboard)/admin/noi-dung", "(dashboard)/admin/content"],
  ["(dashboard)/admin/tim-kiem", "(dashboard)/admin/search"],
];

async function exists(candidate) {
  try {
    await access(candidate);
    return true;
  } catch {
    return false;
  }
}

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) => {
      const candidate = path.join(directory, entry.name);
      if (entry.isDirectory()) return sourceFiles(candidate);
      return /\.(?:ts|tsx|mjs|py)$/.test(entry.name) ? [candidate] : [];
    }),
  );
  return nested.flat();
}

test("only English canonical frontend route directories exist", async () => {
  for (const [legacy, canonical] of routeMigrations) {
    const legacyFiles = (await exists(path.join(appRoot, legacy)))
      ? await sourceFiles(path.join(appRoot, legacy))
      : [];
    const canonicalFiles = (await exists(path.join(appRoot, canonical)))
      ? await sourceFiles(path.join(appRoot, canonical))
      : [];
    assert.equal(legacyFiles.length, 0, legacy);
    assert.notEqual(canonicalFiles.length, 0, canonical);
  }
});

test("frontend source contains no links or rewrites to removed routes", async () => {
  const forbidden =
    /\/(?:quy-trinh|chinh-sach|thu-vien|tai-san|ban-do|kiem-tra|binh-chon|tim-kiem|ho-so|tham-dinh|hoi-dong|chung-thu|thanh-toan|thong-bao|tai-khoan|lich-su-(?:binh-chon|hoat-dong)|admin\/(?:bao-cao|binh-chon|noi-dung|tim-kiem))(?:[/?`"']|$)/;

  for (const file of await sourceFiles(sourceRoot)) {
    if (/\.(?:test|spec)\.(?:ts|tsx|mjs)$/.test(file)) continue;
    const source = await readFile(file, "utf8");
    assert.doesNotMatch(source, forbidden, file);
  }
  for (const file of await sourceFiles("frontend/e2e")) {
    const source = await readFile(file, "utf8");
    assert.doesNotMatch(source, forbidden, file);
  }

  const config = await readFile("frontend/next.config.ts", "utf8");
  assert.doesNotMatch(
    config,
    /destination:\s*"\/(?:ho-so|tham-dinh|hoi-dong|chung-thu)/,
  );
});

test("backend route literals use lowercase English resource segments", async () => {
  const routeLiteral =
    /@router\.(?:get|post|put|patch|delete)\(\s*["']([^"']*)/g;
  for (const file of await sourceFiles("backend/app")) {
    if (!file.endsWith(".py")) continue;
    const source = await readFile(file, "utf8");
    for (const match of source.matchAll(routeLiteral)) {
      assert.match(
        match[1],
        /^(?:|\/(?:[a-z][a-z0-9.-]*|\{[a-zA-Z][a-zA-Z0-9_]*\})(?:\/(?:[a-z][a-z0-9.-]*|\{[a-zA-Z][a-zA-Z0-9_]*\}))*)$/,
        file,
      );
    }
  }
});
