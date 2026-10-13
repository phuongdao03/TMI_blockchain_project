import { reviewCriteria } from "@/components/reviews/five-t-rubric";
import type {
  CriterionVerdictOutcome,
  ReviewData,
  ReviewSnapshot,
} from "@/lib/api/types";

const verdictLabels: Record<CriterionVerdictOutcome, string> = {
  MEETS: "Đáp ứng",
  NEEDS_CLARIFICATION: "Cần làm rõ hoặc bổ sung",
  DOES_NOT_MEET: "Không đáp ứng",
  NOT_APPLICABLE: "Không áp dụng",
};

const gateLabels = {
  PASS: "Đáp ứng",
  FAIL: "Không đáp ứng",
  NOT_APPLICABLE: "Không áp dụng",
} as const;

interface ReportCriterion {
  key: string;
  label: string;
  result: string;
  rationale: string;
  evidenceMediaIds: string[];
}

export function ReviewReportDetails({
  review,
  snapshot,
}: {
  review: ReviewData;
  snapshot: ReviewSnapshot;
}) {
  const rubric = snapshot.dossier.dossierType?.reviewRubric;
  const rows: ReportCriterion[] = [];

  if (rubric) {
    for (const gate of rubric.gates) {
      const answer = review.gateAnswers?.[gate.key];
      if (!answer) continue;
      rows.push({
        key: `gate-${gate.key}`,
        label: gate.label,
        result: gateLabels[answer.outcome],
        rationale: answer.rationale,
        evidenceMediaIds: answer.evidenceMediaIds,
      });
    }
    for (const criterion of rubric.criteria) {
      const verdict = review.criterionVerdicts?.[criterion.key];
      const specialist = review.specialistAnswers?.[criterion.key];
      if (verdict) {
        rows.push({
          key: criterion.key,
          label: criterion.label,
          result: verdictLabels[verdict.outcome],
          rationale: verdict.rationale,
          evidenceMediaIds: verdict.evidenceMediaIds,
        });
      } else if (specialist) {
        rows.push({
          key: criterion.key,
          label: criterion.label,
          result: `${specialist.score}/5 điểm`,
          rationale: specialist.rationale,
          evidenceMediaIds: specialist.evidenceMediaIds,
        });
      }
    }
  }
  for (const criterion of reviewCriteria) {
    const rationale = review.criterionComments?.[criterion.key];
    if (!rationale) continue;
    const score = review[criterion.scoreKey];
    rows.push({
      key: `five-t-${criterion.key}`,
      label: rubric ? `5T · ${criterion.label}` : criterion.label,
      result: score === null ? "Chưa chấm điểm" : `${score}/20 điểm`,
      rationale,
      evidenceMediaIds: review.criterionEvidence?.[criterion.key] ?? [],
    });
  }

  if (!rows.length) return null;

  const evidenceTitles = new Map(
    snapshot.evidences.map((evidence) => [
      evidence.mediaAssetId,
      evidence.title,
    ]),
  );

  return (
    <section
      aria-label="Nhận định theo từng tiêu chí"
      className="mt-5 border-t border-[var(--theme-border)] pt-5"
    >
      <h3 className="font-bold">Nhận định theo từng tiêu chí</h3>
      <ol className="mt-3 divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)]">
        {rows.map((row, index) => (
          <li
            className="grid gap-2 py-4 text-sm md:grid-cols-[minmax(12rem,0.3fr)_minmax(0,1fr)] md:gap-5"
            key={row.key}
          >
            <div>
              <p className="font-bold">
                <span className="mr-2 text-[var(--theme-accent)]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {row.label}
              </p>
              <p className="mt-1 font-semibold text-[var(--theme-accent)]">
                {row.result}
              </p>
            </div>
            <div className="min-w-0">
              <p className="whitespace-pre-wrap leading-6">{row.rationale}</p>
              {row.evidenceMediaIds.length ? (
                <p className="mt-2 text-xs leading-5 text-[var(--theme-muted)]">
                  Tài liệu dẫn chiếu:{" "}
                  {row.evidenceMediaIds
                    .map(
                      (mediaId) =>
                        evidenceTitles.get(mediaId) ??
                        "Tài liệu không còn trong phiên bản này",
                    )
                    .join("; ")}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
