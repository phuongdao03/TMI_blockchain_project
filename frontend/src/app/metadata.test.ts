import { describe, expect, it } from "vitest";

import { metadata } from "@/app/layout";

describe("application metadata", () => {
  it("uses the current THV logo as the browser and Apple icon", () => {
    expect(metadata.icons).toEqual({
      icon: "/favicon-logo.png",
      apple: "/apple-touch-logo.png",
    });
  });
});
