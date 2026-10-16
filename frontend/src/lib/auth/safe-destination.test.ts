import { describe, expect, it } from "vitest";

import { safeLocalDestination } from "@/lib/auth/safe-destination";

describe("safeLocalDestination", () => {
  it("keeps a local path and query", () => {
    expect(
      safeLocalDestination("/community/new?category=heritage", "/workspace"),
    ).toBe("/community/new?category=heritage");
  });

  it("preserves encoded query delimiters without decoding them", () => {
    expect(
      safeLocalDestination(
        "/community/search?q=folk%26jazz&tag=sea%20salt",
        "/workspace",
      ),
    ).toBe("/community/search?q=folk%26jazz&tag=sea%20salt");
  });

  it.each([
    "https://outside.example/path",
    "//outside.example/path",
    "/%2f%2foutside.example/path",
    "/\\outside.example/path",
    "/bad%encoding",
    "/community#editor",
  ])("rejects unsafe destination %s", (value) => {
    expect(safeLocalDestination(value, "/workspace")).toBe("/workspace");
  });
});
