"use client";

import {
  AlertCircle,
  CheckCircle2,
  LoaderCircle,
  Save,
  Send,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { ReviewEvidenceAssessments } from "@/components/reviews/review-evidence-assessments";
import { ReviewEvidenceSelect } from "@/components/reviews/review-evidence-select";
import { useReviewAutosave } from "@/components/reviews/use-review-autosave";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import type {
  CriterionVerdict,
  CriterionVerdictOutcome,
  EvidenceAssessment,
  ReviewData,
  ReviewDraft,
  ReviewEvidenceSnapshot,
  ReviewGateAnswer,
  ReviewRecommendation,
  ReviewRubric,
} from "@/lib/api/types";

type LocalVerdict = Omit<CriterionVerdict, "outcome"> & {
  outcome: CriterionVerdictOutcome | "";
};

const outcomeOptions: Array<{
  value: CriterionVerdictOutcome;
  label: string;
}> = [
  { value: "MEETS", label: "Đáp ứng" },
  { value: "NEEDS_CLARIFICATION", label: "Cần làm rõ hoặc bổ sung" },
  { value: "DOES_NOT_MEET", label: "Không đáp ứng" },
  { value: "NOT_APPLICABLE", label: "Không áp dụng" },
];

function recommendationFor(
  rubric: ReviewRubric,
  verdicts: Record<string, LocalVerdict>,
  gates: Record<string, ReviewGateAnswer>,
): ReviewRecommendation | null {
  if (rubric.criteria.some(({ key }) => !verdicts[key]?.outcome)) return null;
  const requiredGateFailed = rubric.gates.some(
    ({ key, required }) =>
      required !== false &&
      gates[key]?.outcome &&
      gates[key].outcome !== "PASS",
  );
  const outcomes = rubric.criteria.map(({ key }) => verdicts[key]!.outcome);
  if (requiredGateFailed || outcomes.includes("DOES_NOT_MEET")) return "REJECT";
  if (outcomes.includes("NEEDS_CLARIFICATION")) return "SUPPLEMENT";
  if (outcomes.every((outcome) => outcome === "NOT_APPLICABLE")) return null;
  return "APPROVE";
}

function resultLabel(value: ReviewRecommendation | null) {
  if (value === "APPROVE") return "Đề nghị phê duyệt";
  if (value === "SUPPLEMENT") return "Yêu cầu bổ sung";
  if (value === "REJECT") return "Đề nghị từ chối";
  return "Chưa đủ thông tin để kết luận";
}

export function VerdictReviewForm({
  evidences,
  initialReview,
  isSaving,
  isSubmitting,
  onSave,
  onSubmit,
  readOnly,
  requireEvidenceAssessments,
  rubric,
  saveError,
}: {
  evidences: ReviewEvidenceSnapshot[];
  initialReview: ReviewData | null;
  isSaving: boolean;
  isSubmitting: boolean;
  onSave: (draft: ReviewDraft) => Promise<void>;
  onSubmit: () => Promise<void>;
  readOnly: boolean;
  requireEvidenceAssessments: boolean;
  rubric: ReviewRubric;
  saveError?: Error | null;
}) {
  const [verdicts, setVerdicts] = useState<Record<string, LocalVerdict>>(() =>
    Object.fromEntries(
      Object.entries(initialReview?.criterionVerdicts ?? {}).map(
        ([key, value]) => [key, value],
      ),
    ),
  );
  const [gates, setGates] = useState<Record<string, ReviewGateAnswer>>(
    () => initialReview?.gateAnswers ?? {},
  );
  const [assessments, setAssessments] = useState<
    Record<string, EvidenceAssessment>
  >(() => initialReview?.evidenceAssessments ?? {});
  const [applicantFeedback, setApplicantFeedback] = useState(
    initialReview?.applicantFeedback ?? "",
  );
  const [privateNote, setPrivateNote] = useState(
    initialReview?.privateNote ?? "",
  );
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState("");
  const recommendation = useMemo(
    () => recommendationFor(rubric, verdicts, gates),
    [gates, rubric, verdicts],
  );

  const validationIssues = useMemo(() => {
    const issues: string[] = [];
    for (const criterion of rubric.criteria) {
      const answer = verdicts[criterion.key];
      if (!answer?.outcome) {
        issues.push(`${criterion.label}: chưa chọn kết luận.`);
        continue;
      }
      if (answer.rationale.trim().length < 20) {
        issues.push(
          `${criterion.label}: nhận định cần ít nhất 20 ký tự (hiện có ${answer.rationale.trim().length}).`,
        );
      }
      if (
        answer.outcome !== "NOT_APPLICABLE" &&
        answer.evidenceMediaIds.length === 0
      ) {
        issues.push(`${criterion.label}: chưa chọn tài liệu dẫn chiếu.`);
      }
    }
    for (const gate of rubric.gates) {
      const rationaleLength = gates[gate.key]?.rationale.trim().length ?? 0;
      if (rationaleLength < 20) {
        issues.push(
          `${gate.label}: căn cứ cần ít nhất 20 ký tự (hiện có ${rationaleLength}).`,
        );
      }
    }
    if (requireEvidenceAssessments) {
      for (const evidence of evidences) {
        const assessment = assessments[evidence.mediaAssetId];
        if (!assessment || assessment.status === "UNREVIEWED") {
          issues.push(`${evidence.title}: chưa ghi nhận kết quả kiểm tra tệp.`);
        }
      }
    }
    if (recommendation === null && issues.length === 0) {
      issues.push("Cần có ít nhất một tiêu chí áp dụng cho hồ sơ.");
    }
    if (
      recommendation !== null &&
      recommendation !== "APPROVE" &&
      applicantFeedback.trim().length < 20
    ) {
      issues.push(
        `Phản hồi gửi người nộp cần ít nhất 20 ký tự (hiện có ${applicantFeedback.trim().length}).`,
      );
    }
    return issues;
  }, [
    applicantFeedback,
    assessments,
    evidences,
    gates,
    recommendation,
    requireEvidenceAssessments,
    rubric.criteria,
    rubric.gates,
    verdicts,
  ]);

  const buildDraft = useCallback((): ReviewDraft => {
    const criterionVerdicts = Object.fromEntries(
      Object.entries(verdicts)
        .filter(([, answer]) => answer.outcome)
        .map(([key, answer]) => [key, answer as CriterionVerdict]),
    );
    return {
      truthScore: null,
      transparencyScore: null,
      ownershipScore: null,
      professionalismScore: null,
      respectScore: null,
      criterionComments: {},
      criterionEvidence: {},
      findings: initialReview?.findings ?? [],
      checklistAnswers: initialReview?.checklistAnswers ?? {},
      applicantFeedback: applicantFeedback.trim() || null,
      recommendation,
      privateNote: privateNote.trim() || null,
      gateAnswers: gates,
      specialistAnswers: {},
      criterionVerdicts,
      evidenceAssessments: assessments,
    };
  }, [
    applicantFeedback,
    assessments,
    gates,
    initialReview,
    privateNote,
    recommendation,
    verdicts,
  ]);

  const autosaveDraft = useMemo(() => buildDraft(), [buildDraft]);
  useReviewAutosave({ draft: autosaveDraft, onSave, readOnly });

  const complete = validationIssues.length === 0;
  const reviewedFiles = evidences.filter(
    (evidence) =>
      assessments[evidence.mediaAssetId]?.status &&
      assessments[evidence.mediaAssetId]?.status !== "UNREVIEWED",
  ).length;
  const completedCriteria = rubric.criteria.filter(({ key }) => {
    const answer = verdicts[key];
    return (
      answer?.outcome &&
      answer.rationale.trim().length >= 20 &&
      (answer.outcome === "NOT_APPLICABLE" ||
        answer.evidenceMediaIds.length > 0)
    );
  }).length;

  const firstInvalidFieldId = useMemo(() => {
    for (const criterion of rubric.criteria) {
      const answer = verdicts[criterion.key];
      if (!answer?.outcome) return `verdict-outcome-${criterion.key}`;
      if (answer.rationale.trim().length < 20) {
        return `verdict-rationale-${criterion.key}`;
      }
      if (
        answer.outcome !== "NOT_APPLICABLE" &&
        answer.evidenceMediaIds.length === 0
      ) {
        return `verdict-outcome-${criterion.key}`;
      }
    }
    for (const gate of rubric.gates) {
      if ((gates[gate.key]?.rationale.trim().length ?? 0) < 20) {
        return `verdict-gate-rationale-${gate.key}`;
      }
    }
    if (
      recommendation !== null &&
      recommendation !== "APPROVE" &&
      applicantFeedback.trim().length < 20
    ) {
      return "verdict-feedback";
    }
    return null;
  }, [
    applicantFeedback,
    gates,
    recommendation,
    rubric.criteria,
    rubric.gates,
    verdicts,
  ]);

  async function prepareSubmit() {
    if (!complete) {
      setError(validationIssues[0] ?? "Phiếu còn nội dung cần hoàn tất.");
      if (firstInvalidFieldId) {
        document.getElementById(firstInvalidFieldId)?.focus();
      }
      return;
    }
    try {
      await onSave(buildDraft());
      setError("");
      setConfirmOpen(true);
    } catch {
      setError("Chưa thể lưu phiếu. Vui lòng thử lại.");
    }
  }

  return (
    <>
      <section className="pt-6 text-[var(--theme-text)]">
        <header className="pb-6">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--theme-accent)]">
            Kết luận theo tiêu chí
          </p>
          <h2 className="mt-2 text-2xl font-bold">Phiếu thẩm định hồ sơ</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
            Kiểm tra tệp, chọn kết luận cho từng tiêu chí rồi gửi kết quả. Bản
            nháp được lưu trong khi bạn làm việc.
          </p>
          <div
            aria-label="Tiến độ thẩm định"
            className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold"
          >
            <span>
              Tệp đã kiểm tra {reviewedFiles}/{evidences.length}
            </span>
            <span>
              Tiêu chí hoàn thành {completedCriteria}/{rubric.criteria.length}
            </span>
            <span
              className={
                complete ? "text-emerald-700" : "text-[var(--theme-muted)]"
              }
            >
              {complete
                ? "Sẵn sàng gửi"
                : `${validationIssues.length} mục cần hoàn tất`}
            </span>
          </div>
          {!complete ? (
            <p
              className="mt-2 text-xs leading-5 text-[var(--theme-muted)]"
              role="status"
            >
              Cần làm tiếp: {validationIssues[0]}
            </p>
          ) : null}
        </header>
        <form className="space-y-9">
          <ReviewEvidenceAssessments
            assessments={assessments}
            evidences={evidences}
            onChange={setAssessments}
            readOnly={readOnly}
          />

          {rubric.gates.length ? (
            <section className="space-y-3" aria-labelledby="review-conditions">
              <h3 className="text-lg font-bold" id="review-conditions">
                Điều kiện tiếp nhận
              </h3>
              <div className="space-y-8">
                {rubric.gates.map((gate) => {
                  const answer = gates[gate.key] ?? {
                    outcome: "PASS" as const,
                    rationale: "",
                    evidenceMediaIds: [],
                  };
                  return (
                    <fieldset
                      className="min-w-0 border-0 px-0 py-0"
                      disabled={readOnly}
                      key={gate.key}
                    >
                      <legend className="px-1 font-bold">{gate.label}</legend>
                      <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                        {gate.description}
                      </p>
                      <div className="mt-4 grid gap-4 md:grid-cols-[minmax(12rem,0.35fr)_minmax(0,1fr)]">
                        <select
                          aria-label={`Kết quả ${gate.label}`}
                          className="min-h-11 self-start rounded-lg border bg-[var(--theme-surface)] px-3"
                          onChange={(event) =>
                            setGates((current) => ({
                              ...current,
                              [gate.key]: {
                                ...answer,
                                outcome: event.target
                                  .value as ReviewGateAnswer["outcome"],
                              },
                            }))
                          }
                          value={answer.outcome}
                        >
                          <option value="PASS">Đáp ứng</option>
                          <option value="FAIL">Không đáp ứng</option>
                          <option value="NOT_APPLICABLE">Không áp dụng</option>
                        </select>
                        <div>
                          <textarea
                            aria-label={`Căn cứ ${gate.label}`}
                            className="min-h-28 w-full resize-y rounded-lg border bg-[var(--theme-surface)] p-3 leading-6"
                            id={`verdict-gate-rationale-${gate.key}`}
                            maxLength={2_000}
                            onChange={(event) =>
                              setGates((current) => ({
                                ...current,
                                [gate.key]: {
                                  ...answer,
                                  rationale: event.target.value,
                                },
                              }))
                            }
                            placeholder="Nêu kết quả đối chiếu (tối thiểu 20 ký tự)"
                            value={answer.rationale}
                          />
                          <p className="mt-1 text-right text-xs text-[var(--theme-muted)]">
                            {answer.rationale.trim().length >= 20
                              ? "Đủ độ dài căn cứ"
                              : `Cần thêm ${20 - answer.rationale.trim().length} ký tự`}
                          </p>
                        </div>
                      </div>
                      <ReviewEvidenceSelect
                        disabled={readOnly}
                        evidences={evidences}
                        label={gate.label}
                        onChange={(ids) =>
                          setGates((current) => ({
                            ...current,
                            [gate.key]: { ...answer, evidenceMediaIds: ids },
                          }))
                        }
                        value={answer.evidenceMediaIds}
                      />
                    </fieldset>
                  );
                })}
              </div>
            </section>
          ) : null}

          <section className="space-y-3" aria-labelledby="review-verdicts">
            <div>
              <h3 className="text-lg font-bold" id="review-verdicts">
                Kết luận từng tiêu chí
              </h3>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                Đánh giá dựa trên tài liệu thực tế của hồ sơ.
              </p>
            </div>
            <div className="space-y-10">
              {rubric.criteria.map((criterion, index) => {
                const answer = verdicts[criterion.key] ?? {
                  outcome: "",
                  rationale: "",
                  evidenceMediaIds: [],
                };
                return (
                  <fieldset
                    className="min-w-0 border-0 px-0 py-0"
                    disabled={readOnly}
                    key={criterion.key}
                  >
                    <legend className="px-1 font-bold">
                      <span className="mr-2 text-[var(--theme-accent)]">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      {criterion.label}
                    </legend>
                    <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
                      {criterion.description}
                    </p>
                    <div className="mt-4 grid gap-4 md:grid-cols-[minmax(12rem,0.35fr)_minmax(0,1fr)]">
                      <select
                        aria-label={`Kết luận ${criterion.label}`}
                        className="min-h-11 self-start rounded-lg border bg-[var(--theme-surface)] px-3"
                        id={`verdict-outcome-${criterion.key}`}
                        onChange={(event) =>
                          setVerdicts((current) => ({
                            ...current,
                            [criterion.key]: {
                              ...answer,
                              outcome: event.target
                                .value as LocalVerdict["outcome"],
                            },
                          }))
                        }
                        value={answer.outcome}
                      >
                        <option value="">Chọn kết luận</option>
                        {outcomeOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <div>
                        <textarea
                          aria-label={`Nhận định ${criterion.label}`}
                          className="min-h-24 w-full rounded-lg border bg-[var(--theme-surface)] p-3"
                          id={`verdict-rationale-${criterion.key}`}
                          maxLength={2_000}
                          onChange={(event) =>
                            setVerdicts((current) => ({
                              ...current,
                              [criterion.key]: {
                                ...answer,
                                rationale: event.target.value,
                              },
                            }))
                          }
                          placeholder="Nêu điều đã kiểm tra và căn cứ kết luận (tối thiểu 20 ký tự)"
                          value={answer.rationale}
                        />
                        <p className="mt-1 text-right text-xs text-[var(--theme-muted)]">
                          {answer.rationale.trim().length >= 20
                            ? "Đủ độ dài căn cứ"
                            : `Cần thêm ${20 - answer.rationale.trim().length} ký tự`}
                        </p>
                      </div>
                    </div>
                    <ReviewEvidenceSelect
                      disabled={readOnly || answer.outcome === "NOT_APPLICABLE"}
                      evidences={evidences}
                      label={criterion.label}
                      onChange={(ids) =>
                        setVerdicts((current) => ({
                          ...current,
                          [criterion.key]: { ...answer, evidenceMediaIds: ids },
                        }))
                      }
                      value={answer.evidenceMediaIds}
                    />
                  </fieldset>
                );
              })}
            </div>
          </section>

          <section
            className="grid scroll-mt-24 gap-4 border-t border-[var(--theme-border)] pt-6 md:grid-cols-2"
            id="review-final-result"
          >
            <div
              className="border-l-2 border-[var(--theme-accent)] pl-4"
              role="status"
            >
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
                Kết quả từ các tiêu chí
              </p>
              <p className="mt-2 text-lg font-bold">
                {resultLabel(recommendation)}
              </p>
            </div>
            <div>
              <label className="text-sm font-bold" htmlFor="verdict-feedback">
                Phản hồi gửi người nộp
              </label>
              <textarea
                className="mt-2 min-h-24 w-full rounded-xl border bg-[var(--theme-surface)] p-3"
                disabled={readOnly}
                id="verdict-feedback"
                onChange={(event) => setApplicantFeedback(event.target.value)}
                placeholder="Nêu rõ nội dung cần bổ sung hoặc lý do không đáp ứng"
                value={applicantFeedback}
              />
            </div>
            <div className="md:col-span-2">
              <label
                className="text-sm font-bold"
                htmlFor="verdict-private-note"
              >
                Ghi chú nội bộ
              </label>
              <textarea
                className="mt-2 min-h-20 w-full rounded-xl border bg-[var(--theme-surface)] p-3"
                disabled={readOnly}
                id="verdict-private-note"
                onChange={(event) => setPrivateNote(event.target.value)}
                value={privateNote}
              />
            </div>
          </section>

          {error ? (
            <p className="text-sm font-semibold text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex flex-col justify-between gap-4 pt-2 sm:flex-row sm:items-center">
            <p
              aria-live="polite"
              className="flex items-center gap-2 text-xs font-semibold text-[var(--theme-muted)]"
              data-testid="review-save-status"
              role={saveError ? "alert" : "status"}
            >
              {readOnly ? (
                <>
                  <CheckCircle2 className="size-4" />
                  Kết quả đã gửi.
                </>
              ) : saveError ? (
                <>
                  <AlertCircle className="size-4 text-red-700" />
                  Chưa lưu được bản nháp.
                </>
              ) : isSaving ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Đang lưu thay đổi…
                </>
              ) : (
                <>
                  <Save className="size-4" />
                  Đã lưu bản nháp.
                </>
              )}
            </p>
            {!readOnly ? (
              <Button
                disabled={isSaving || isSubmitting}
                onClick={() => void prepareSubmit()}
                type="button"
              >
                <Send className="size-4" />
                Gửi kết quả thẩm định
              </Button>
            ) : null}
          </div>
        </form>
      </section>
      <ConfirmationDialog
        confirmLabel="Xác nhận gửi"
        description="Sau khi gửi, kết luận và tài liệu dẫn chiếu sẽ được khóa."
        isPending={isSubmitting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() =>
          void onSubmit()
            .then(() => setConfirmOpen(false))
            .catch(() => undefined)
        }
        open={confirmOpen}
        title="Xác nhận gửi kết quả"
      />
    </>
  );
}
