import { describe, expect, it } from "vitest";

import { featureAvailability, publicV1Features } from "./v1-features";

describe("V1 feature registry", () => {
  it("keeps browsing and account access active in preview", () => {
    expect(featureAvailability("catalog", "preview")).toBe("enabled");
    expect(featureAvailability("authentication", "preview")).toBe("enabled");
  });

  it("keeps submission pending without exposing retired voting", () => {
    expect(featureAvailability("submission", "preview")).toBe("coming-soon");
    expect(featureAvailability("payment", "preview")).toBe("hidden");
    expect("voting" in publicV1Features).toBe(false);
  });
});
