"use client";

import { CheckCircle2, LoaderCircle, Save, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ReviewEvidenceAssessments } from "@/components/reviews/review-evidence-assessments";
import { ReviewEvidenceSelect } from "@/components/reviews/review-evidence-select";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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

  const lastSaved = useRef(JSON.stringify(buildDraft()));
  useEffect(() => {
    if (readOnly) return;
    const draft = buildDraft();
    const serialized = JSON.stringify(draft);
    if (serialized === lastSaved.current) return;
    const timer = window.setTimeout(() => {
      void onSave(draft)
        .then(() => {
          lastSaved.current = serialized;
        })
        .catch(() => undefined);
    }, 650);
    return () => window.clearTimeout(timer);
  }, [buildDraft, onSave, readOnly]);

  const complete =
    recommendation !== null &&
    rubric.criteria.every(({ key }) => {
      const answer = verdicts[key];
      return (
        Boolean(answer?.outcome) &&
        (answer?.rationale.trim().length ?? 0) >= 20 &&
        (answer?.outcome === "NOT_APPLICABLE" ||
          (answer?.evidenceMediaIds.length ?? 0) > 0)
      );
    }) &&
    rubric.gates.every(
      ({ key }) => (gates[key]?.rationale.trim().length ?? 0) >= 20,
    ) &&
    (!requireEvidenceAssessments ||
      evidences.every(({ mediaAssetId }) => {
        const assessment = assessments[mediaAssetId];
        return assessment && assessment.status !== "UNREVIEWED";
      })) &&
    (recommendation === "APPROVE" || applicantFeedback.trim().length >= 20);

  async function prepareSubmit() {
    if (!complete) {
      setError(
        "Hãy hoàn tất kết luận, căn cứ và phản hồi cần thiết trước khi gửi.",
      );
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
      <Card className="overflow-hidden">
        <header className="border-b bg-ink-950 px-5 py-6 text-white sm:px-8">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
            Kết luận theo tiêu chí
          </p>
          <h2 className="mt-2 text-2xl font-bold">Phiếu thẩm định hồ sơ</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            Chọn kết luận rõ ràng cho từng tiêu chí và dẫn tài liệu đã kiểm tra.
            Phiếu này không sử dụng điểm số.
          </p>
        </header>
        <form className="space-y-6 p-5 sm:p-8">
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
              {rubric.gates.map((gate) => {
                const answer = gates[gate.key] ?? {
                  outcome: "PASS" as const,
                  rationale: "",
                  evidenceMediaIds: [],
                };
                return (
                  <fieldset
                    className="rounded-xl border p-4"
                    disabled={readOnly}
                    key={gate.key}
                  >
                    <legend className="px-1 font-bold">{gate.label}</legend>
                    <p className="text-sm text-neutral-600">
                      {gate.description}
                    </p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-[13rem_1fr]">
                      <select
                        aria-label={`Kết quả ${gate.label}`}
                        className="min-h-11 rounded-lg border bg-[var(--theme-surface)] px-3"
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
                      <textarea
                        aria-label={`Căn cứ ${gate.label}`}
                        className="min-h-20 rounded-lg border bg-[var(--theme-surface)] p-3"
                        onChange={(event) =>
                          setGates((current) => ({
                            ...current,
                            [gate.key]: {
                              ...answer,
                              rationale: event.target.value,
                            },
                          }))
                        }
                        placeholder="Nêu kết quả đối chiếu"
                        value={answer.rationale}
                      />
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
            </section>
          ) : null}

          <section className="space-y-3" aria-labelledby="review-verdicts">
            <div>
              <h3 className="text-lg font-bold" id="review-verdicts">
                Kết luận từng tiêu chí
              </h3>
              <p className="mt-1 text-sm text-neutral-600">
                Đánh giá dựa trên tài liệu thực tế của hồ sơ.
              </p>
            </div>
            {rubric.criteria.map((criterion, index) => {
              const answer = verdicts[criterion.key] ?? {
                outcome: "",
                rationale: "",
                evidenceMediaIds: [],
              };
              return (
                <fieldset
                  className="rounded-2xl border bg-[var(--theme-elevated)] p-4 sm:p-5"
                  disabled={readOnly}
                  key={criterion.key}
                >
                  <legend className="px-1 font-bold">
                    <span className="mr-2 text-primary-700">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    {criterion.label}
                  </legend>
                  <p className="text-sm text-neutral-600">
                    {criterion.description}
                  </p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-[15rem_1fr]">
                    <select
                      aria-label={`Kết luận ${criterion.label}`}
                      className="min-h-11 rounded-lg border bg-[var(--theme-surface)] px-3"
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
                    <textarea
                      aria-label={`Nhận định ${criterion.label}`}
                      className="min-h-24 rounded-lg border bg-[var(--theme-surface)] p-3"
                      onChange={(event) =>
                        setVerdicts((current) => ({
                          ...current,
                          [criterion.key]: {
                            ...answer,
                            rationale: event.target.value,
                          },
                        }))
                      }
                      placeholder="Nêu điều đã kiểm tra và căn cứ kết luận"
                      value={answer.rationale}
                    />
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
          </section>

          <section className="grid gap-4 rounded-2xl border p-5 md:grid-cols-2">
            <div
              className="rounded-xl bg-[var(--theme-elevated)] p-4"
              role="status"
            >
              <p className="text-xs font-bold uppercase tracking-wider text-neutral-600">
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
          <div className="flex flex-col justify-between gap-4 border-t pt-5 sm:flex-row sm:items-center">
            <p
              aria-live="polite"
              className="flex items-center gap-2 text-xs font-semibold text-neutral-500"
            >
              {readOnly ? (
                <>
                  <CheckCircle2 className="size-4" />
                  Kết quả đã gửi.
                </>
              ) : isSaving ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Đang tự động lưu…
                </>
              ) : (
                <>
                  <Save className="size-4" />
                  Bản nháp được tự động lưu.
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
      </Card>
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
