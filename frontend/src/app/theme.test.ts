import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(
  resolve(process.cwd(), "src/app/globals.css"),
  "utf8",
);

describe("red identity theme", () => {
  it.each([
    ["--color-primary-700", "#b91c1c"],
    ["--color-primary-600", "#dc2626"],
    ["--color-primary-500", "#ef4444"],
    ["--color-primary-100", "#fee2e2"],
    ["--color-primary-50", "#fef2f2"],
    ["--color-accent-gold", "#d4a72c"],
    ["--color-neutral-950", "#0f172a"],
    ["--color-neutral-700", "#334155"],
    ["--color-neutral-500", "#64748b"],
    ["--color-neutral-200", "#e2e8f0"],
    ["--color-surface", "#ffffff"],
    ["--color-background", "#f8fafc"],
    ["--color-success", "#15803d"],
    ["--color-warning", "#b45309"],
    ["--color-error", "#b91c1c"],
    ["--color-ink-950", "#070a12"],
    ["--color-ink-900", "#0c1220"],
    ["--color-ink-800", "#141d2e"],
    ["--color-gold-300", "#f3d675"],
  ])("defines %s as %s", (token, value) => {
    expect(stylesheet).toContain(`${token}: ${value};`);
  });

  it("provides a visible keyboard focus treatment", () => {
    expect(stylesheet).toContain(":focus-visible");
    expect(stylesheet).toContain("outline-offset");
  });

  it("disables branded motion when reduced motion is requested", () => {
    expect(stylesheet).toContain(".evidence-register:hover .evidence-document");
    expect(stylesheet).toContain("transition-duration: 0.01ms !important");
  });
});
