import { describe, expect, it } from "vitest";

import { previewWorks, resolvePreviewWork } from "@/lib/preview-catalog";

describe("preview catalog", () => {
  it("contains curated introductory works without verification claims", () => {
    expect(previewWorks).toHaveLength(3);
    for (const work of previewWorks) {
      const detail = resolvePreviewWork(work.slug);
      expect(detail?.certificate).toBeNull();
      expect(detail?.proof).toBeNull();
      expect(detail?.shortDescription).toContain("giới thiệu");
    }
  });

  it("does not resolve unknown preview slugs", () => {
    expect(resolvePreviewWork("unknown-work")).toBeUndefined();
  });
});
