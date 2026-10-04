import { describe, expect, it } from "vitest";

import { metadata } from "@/app/layout";

describe("application metadata", () => {
  it("uses the approved THV emblem as the browser icon", () => {
    expect(metadata.icons).toEqual({
      icon: "/assets/brand/thv-certificate-seal.png",
      apple: "/assets/brand/thv-certificate-seal.png",
    });
  });
});
