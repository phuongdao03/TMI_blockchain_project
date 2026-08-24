import { describe, expect, it } from "vitest";

import {
  isPreviewRelease,
  isPreviewRestrictedPath,
  releaseMode,
} from "@/lib/release-mode";

describe("release mode", () => {
  it("keeps preview opt-in so an unset or invalid production build cannot serve demo data", () => {
    expect(releaseMode()).toBe("full");
    expect(releaseMode("unexpected")).toBe("full");
    expect(isPreviewRelease("unexpected")).toBe(false);
  });

  it("enables full workflows only with the explicit full value", () => {
    expect(releaseMode("full")).toBe("full");
    expect(isPreviewRelease("full")).toBe(false);
  });

  it("enables preview only with the explicit preview value", () => {
    expect(releaseMode("preview")).toBe("preview");
    expect(isPreviewRelease("preview")).toBe(true);
  });

  it("restricts business workspaces but preserves account and public pages", () => {
    expect(isPreviewRestrictedPath("/dossiers/new")).toBe(true);
    expect(isPreviewRestrictedPath("/payments/order-1")).toBe(true);
    expect(isPreviewRestrictedPath("/admin")).toBe(true);
    expect(isPreviewRestrictedPath("/account")).toBe(false);
    expect(isPreviewRestrictedPath("/works/sample-work")).toBe(false);
  });
});
