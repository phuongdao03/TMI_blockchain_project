import { describe, expect, it } from "vitest";

import { featureAvailability, publicV1Features } from "./v1-features";

describe("V1 feature registry", () => {
  it("keeps browsing and account access active in preview", () => {
    expect(featureAvailability("publicCatalog", "preview")).toBe("enabled");
    expect(featureAvailability("authentication", "preview")).toBe("enabled");
  });

  it("marks voting and submissions as coming soon without enabling payment", () => {
    expect(featureAvailability("voting", "preview")).toBe("coming-soon");
    expect(featureAvailability("submission", "preview")).toBe("coming-soon");
    expect(featureAvailability("payment", "preview")).toBe("hidden");
    expect(publicV1Features.voting.href).toBe("/coming-soon/voting");
  });
});
