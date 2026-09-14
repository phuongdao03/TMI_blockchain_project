import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

describe("PWA service worker policy", () => {
  const source = readFileSync(join(process.cwd(), "public", "sw.js"), "utf8");

  it("only intercepts document navigation and never caches API responses", () => {
    expect(source).toContain('event.request.mode !== "navigate"');
    expect(source).toContain('const OFFLINE_URL = "/offline"');
    expect(source).not.toContain("cache.put(");
    expect(source).not.toContain("/api/");
  });
});
