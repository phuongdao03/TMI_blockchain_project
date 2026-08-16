import { describe, expect, it } from "vitest";

import {
  isPreviewRelease,
  isPreviewRestrictedPath,
  releaseMode,
} from "@/lib/release-mode";

describe("release mode", () => {
  it("fails closed for invalid configured values", () => {
    expect(releaseMode("unexpected")).toBe("preview");
    expect(isPreviewRelease("unexpected")).toBe(true);
  });

  it("enables full workflows only with the explicit full value", () => {
    expect(releaseMode("full")).toBe("full");
    expect(isPreviewRelease("full")).toBe(false);
  });

  it("restricts business workspaces but preserves account and public pages", () => {
    expect(isPreviewRestrictedPath("/dossiers/new")).toBe(true);
    expect(isPreviewRestrictedPath("/payments/order-1")).toBe(true);
    expect(isPreviewRestrictedPath("/admin")).toBe(true);
    expect(isPreviewRestrictedPath("/account")).toBe(false);
    expect(isPreviewRestrictedPath("/works/sample-work")).toBe(false);
  });
});
