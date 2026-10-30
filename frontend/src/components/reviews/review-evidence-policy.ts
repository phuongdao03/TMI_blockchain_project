import type {
  CriterionVerdict,
  EvidenceAssessment,
  ReviewRubric,
} from "@/lib/api/types";

export function criterionRequiresEvidence(outcome: string) {
  return outcome !== "NOT_APPLICABLE" && outcome !== "INSUFFICIENT_BASIS";
}

export function duplicateApprovalRationales(
  answers: Record<string, { outcome: string; rationale: string }>,
) {
  const seen = new Map<string, string>();
  const duplicates = new Set<string>();
  for (const [key, answer] of Object.entries(answers)) {
    if (answer.outcome !== "MEETS") continue;
    const normalized = answer.rationale
      .trim()
      .replace(/\s+/gu, " ")
      .toLowerCase();
    if (!normalized) continue;
    const previous = seen.get(normalized);
    if (previous) {
      duplicates.add(previous);
      duplicates.add(key);
    } else seen.set(normalized, key);
  }
  return duplicates;
}

export function hasRelevantContradiction(
  assessments: Record<string, EvidenceAssessment>,
) {
  return Object.values(assessments).some(
    (assessment) =>
      assessment.status !== "NOT_RELEVANT" &&
      assessment.verification?.outcome === "CONTRADICTED",
  );
}

export function verificationComplete(assessment: EvidenceAssessment) {
  const value = assessment.verification;
  return (
    !value ||
    value.outcome === "UNVERIFIED" ||
    [value.method, value.source, value.scope, value.limitations].every(
      (text) => text.trim().length > 0,
    )
  );
}

export function criterionEvidenceIssue(
  rubric: ReviewRubric,
  criterion: ReviewRubric["criteria"][number],
  answer: Pick<CriterionVerdict, "outcome" | "evidenceMediaIds">,
  assessments: Record<string, EvidenceAssessment>,
): string | null {
  if (rubric.evidencePolicyVersion !== "2026.1") return null;
  if (answer.outcome === "NOT_APPLICABLE" && !criterion.allowNotApplicable) {
    return "bộ tiêu chí không cho phép chọn Không áp dụng.";
  }
  if (answer.outcome !== "MEETS") return null;
  for (const id of answer.evidenceMediaIds) {
    const assessment = assessments[id];
    if (assessment?.status !== "VALID")
      return "tài liệu dẫn chiếu phải phù hợp và không còn yêu cầu làm rõ.";
    const outcome = assessment.verification?.outcome ?? "UNVERIFIED";
    if (["INSUFFICIENT", "CONTRADICTED", "UNVERIFIABLE"].includes(outcome)) {
      return "minh chứng còn thiếu căn cứ hoặc mâu thuẫn chưa giải quyết.";
    }
    if (criterion.verificationRequired && outcome !== "VERIFIED") {
      return "cần hoàn tất kiểm chứng nội dung theo yêu cầu của tiêu chí.";
    }
  }
  return null;
}
