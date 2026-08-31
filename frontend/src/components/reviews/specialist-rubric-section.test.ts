import { describe, expect, it } from "vitest";

import { specialistScore } from "@/components/reviews/specialist-rubric-section";
import type { ReviewRubric } from "@/lib/api/types";

const rubric: ReviewRubric = {
  version: "2026.1",
  title: "Thẩm định tác phẩm",
  gates: [],
  criteria: [
    { key: "originality", label: "Nguyên bản", description: "", weight: 60 },
    { key: "value", label: "Giá trị", description: "", weight: 40 },
  ],
  thresholds: { approveMin: 75, rejectBelow: 50 },
};

describe("specialistScore", () => {
  it("calculates the weighted 0–100 result", () => {
    expect(specialistScore(rubric, {
      originality: { score: 4, rationale: "Đủ căn cứ kiểm chứng nguồn gốc.", evidenceMediaIds: ["a"] },
      value: { score: 3, rationale: "Có giá trị được đối chứng rõ ràng.", evidenceMediaIds: ["b"] },
    })).toBe(72);
  });

  it("does not present a partial score as complete", () => {
    expect(specialistScore(rubric, {})).toBeNull();
  });
});
