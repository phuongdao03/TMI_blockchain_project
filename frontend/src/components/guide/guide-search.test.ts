import { describe, expect, it } from "vitest";

import {
  getHighlightedSegments,
  normalizeGuideSearch,
  toGuideHeadingId,
} from "@/components/guide/guide-search";

describe("guide search helpers", () => {
  it("normalizes Vietnamese accents and case for matching", () => {
    expect(normalizeGuideSearch("  HỒ SƠ   ĐỀ CỬ ")).toBe("ho so de cu");
    expect(normalizeGuideSearch("hồ sơ")).toBe("ho so");
  });

  it("highlights accent-insensitive matches without changing source text", () => {
    expect(getHighlightedSegments("Hồ sơ đề cử", "ho so")).toEqual([
      { text: "Hồ sơ", matched: true },
      { text: " đề cử", matched: false },
    ]);
  });

  it("creates stable heading IDs and disambiguates repeated headings", () => {
    expect(toGuideHeadingId("Tạo hồ sơ đề cử")).toBe("tao-ho-so-de-cu");
    expect(toGuideHeadingId("Tạo hồ sơ đề cử", 2)).toBe("tao-ho-so-de-cu-2");
  });
});
