import { describe, expect, it } from "vitest";

import {
  criterionEvidenceIssue,
  duplicateApprovalRationales,
  verificationComplete,
} from "@/components/reviews/review-evidence-policy";
import type { EvidenceAssessment, ReviewRubric } from "@/lib/api/types";

const criterion = {
  key: "origin",
  label: "Nguồn gốc",
  description: "Đối chiếu nguồn gốc",
  verificationRequired: true,
};
const rubric: ReviewRubric = {
  version: "2026.3",
  title: "Thẩm định",
  assessmentMethod: "VERDICT",
  evidencePolicyVersion: "2026.1",
  gates: [],
  criteria: [criterion],
};
const meets = { outcome: "MEETS" as const, evidenceMediaIds: ["media-1"] };
const verified: EvidenceAssessment = {
  status: "VALID",
  note: "",
  verification: {
    outcome: "VERIFIED",
    method: "So sánh bản thảo",
    source: "Kho tư liệu",
    scope: "Niên đại",
    limitations: "Trong phạm vi nguồn được cung cấp",
  },
};

describe("frozen evidence policy", () => {
  it("requires distinct approval rationales while leaving non-approval explanations usable", () => {
    expect([
      ...duplicateApprovalRationales({
        one: { outcome: "MEETS", rationale: "Cùng một nhận định." },
        two: { outcome: "MEETS", rationale: "  CÙNG một   nhận định. " },
        three: {
          outcome: "INSUFFICIENT_BASIS",
          rationale: "Cùng một nhận định.",
        },
      }),
    ]).toEqual(["one", "two"]);
  });
  it("accepts documented verification and keeps legacy relevance-only records compatible", () => {
    expect(
      criterionEvidenceIssue(rubric, criterion, meets, { "media-1": verified }),
    ).toBeNull();
    expect(
      criterionEvidenceIssue(
        { ...rubric, evidencePolicyVersion: undefined },
        criterion,
        meets,
        {},
      ),
    ).toBeNull();
    expect(verificationComplete({ status: "VALID", note: "" })).toBe(true);
  });

  it.each(["UNREVIEWED", "NOT_RELEVANT", "NEEDS_CLARIFICATION"] as const)(
    "blocks MEETS based on %s evidence",
    (status) => {
      expect(
        criterionEvidenceIssue(rubric, criterion, meets, {
          "media-1": { ...verified, status },
        }),
      ).not.toBeNull();
    },
  );

  it("does not confuse partial verification with completed required verification", () => {
    expect(
      criterionEvidenceIssue(rubric, criterion, meets, {
        "media-1": {
          ...verified,
          verification: { ...verified.verification!, outcome: "PARTIAL" },
        },
      }),
    ).not.toBeNull();
    expect(
      verificationComplete({
        ...verified,
        verification: { ...verified.verification!, source: " " },
      }),
    ).toBe(false);
  });

  it("requires an explicit exception rule before skipping a criterion", () => {
    const answer = { outcome: "NOT_APPLICABLE" as const, evidenceMediaIds: [] };
    expect(
      criterionEvidenceIssue(rubric, criterion, answer, {}),
    ).not.toBeNull();
    expect(
      criterionEvidenceIssue(
        rubric,
        { ...criterion, allowNotApplicable: true },
        answer,
        {},
      ),
    ).toBeNull();
  });
});
