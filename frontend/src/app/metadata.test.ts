import { describe, expect, it } from "vitest";

import { metadata } from "@/app/layout";

describe("application metadata", () => {
  it("uses the approved TMI logo as the browser icon", () => {
    expect(metadata.icons).toEqual({
      icon: "/assets/brand/tmi-group-logo.png",
    });
  });
});
