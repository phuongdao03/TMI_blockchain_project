import { describe, expect, it } from "vitest";

import { decisionGate, scoreBand } from "@/components/reviews/five-t-rubric";

describe("professional 5T decision gates", () => {
  it("requires both the approval total and the criterion floor", () => {
    expect(decisionGate([14, 14, 14, 14, 14], "APPROVE", []).message).toContain("75");
    expect(decisionGate([7, 17, 17, 17, 17], "APPROVE", []).message).toContain("12/20");
    expect(decisionGate([15, 15, 15, 15, 15], "APPROVE", []).valid).toBe(true);
  });

  it("explains score anchors and blocks inconsistent rejection", () => {
    expect(scoreBand(10)?.label).toBe("Đạt có điều kiện");
    expect(decisionGate([12, 12, 12, 12, 12], "REJECT", []).valid).toBe(false);
  });
});
