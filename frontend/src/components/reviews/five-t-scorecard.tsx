"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, LoaderCircle, Save, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import {
  ReviewCompletionChecklist,
  type ReviewChecklistKey,
} from "@/components/reviews/review-completion-checklist";
import { ReviewEvidenceSelect } from "@/components/reviews/review-evidence-select";
import { ReviewFindingsEditor } from "@/components/reviews/review-findings-editor";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import type {
  ReviewData,
  ReviewDraft,
  ReviewEvidenceSnapshot,
  ReviewFinding,
} from "@/lib/api/types";

const scoreMessage = "Điểm phải từ 0 đến 20.";
const scoreSchema = z
  .number()
  .int(scoreMessage)
  .min(0, scoreMessage)
  .max(20, scoreMessage)
  .nullable();
const draftSchema = z.object({
  truthScore: scoreSchema,
  transparencyScore: scoreSchema,
  ownershipScore: scoreSchema,
  professionalismScore: scoreSchema,
  respectScore: scoreSchema,
  criterionComments: z.object({
    truth: z.string().max(2_000),
    transparency: z.string().max(2_000),
    ownership: z.string().max(2_000),
    professionalism: z.string().max(2_000),
    respect: z.string().max(2_000),
  }),
  applicantFeedback: z.string().max(2_000).nullable(),
  recommendation: z.enum(["APPROVE", "SUPPLEMENT", "REJECT"]).nullable(),
  privateNote: z.string().max(5_000).nullable(),
});

type ScorecardValues = z.infer<typeof draftSchema>;
type ScoreKey = Exclude<
  keyof ScorecardValues,
  "criterionComments" | "applicantFeedback" | "recommendation" | "privateNote"
>;
type CriterionKey = keyof ScorecardValues["criterionComments"];
type CriterionEvidence = Record<CriterionKey, string[]>;

const criteria: Array<{
  key: CriterionKey;
  label: string;
  scoreKey: ScoreKey;
  hint: string;
}> = [
  {
    key: "truth",
    label: "Tính đúng đắn",
    scoreKey: "truthScore",
    hint: "Độ chính xác, xác thực và nhất quán của thông tin.",
  },
  {
    key: "transparency",
    label: "Tính minh bạch",
    scoreKey: "transparencyScore",
    hint: "Khả năng truy xuất nguồn gốc và kiểm chứng bằng chứng.",
  },
  {
    key: "ownership",
    label: "Tinh thần trách nhiệm",
    scoreKey: "ownershipScore",
    hint: "Trách nhiệm của chủ thể đối với cam kết và tài sản.",
  },
  {
    key: "professionalism",
    label: "Tính chuyên nghiệp",
    scoreKey: "professionalismScore",
    hint: "Chuẩn mực, năng lực và chất lượng thực hiện.",
  },
  {
    key: "respect",
    label: "Sự tôn trọng",
    scoreKey: "respectScore",
    hint: "Tôn trọng pháp luật, cộng đồng và các bên liên quan.",
  },
];

const checklistKeys: ReviewChecklistKey[] = [
  "evidence_reviewed",
  "criteria_assessed",
  "findings_recorded",
  "similarity_checked",
  "attestation",
];

function defaults(review: ReviewData | null): ScorecardValues {
  return {
    truthScore: review?.truthScore ?? null,
    transparencyScore: review?.transparencyScore ?? null,
    ownershipScore: review?.ownershipScore ?? null,
    professionalismScore: review?.professionalismScore ?? null,
    respectScore: review?.respectScore ?? null,
    criterionComments: {
      truth: review?.criterionComments.truth ?? "",
      transparency: review?.criterionComments.transparency ?? "",
      ownership: review?.criterionComments.ownership ?? "",
      professionalism: review?.criterionComments.professionalism ?? "",
      respect: review?.criterionComments.respect ?? "",
    },
    applicantFeedback: review?.applicantFeedback ?? null,
    recommendation: review?.recommendation ?? null,
    privateNote: review?.privateNote ?? null,
  };
}

function evidenceDefaults(review: ReviewData | null): CriterionEvidence {
  return {
    truth: review?.criterionEvidence.truth ?? [],
    transparency: review?.criterionEvidence.transparency ?? [],
    ownership: review?.criterionEvidence.ownership ?? [],
    professionalism: review?.criterionEvidence.professionalism ?? [],
    respect: review?.criterionEvidence.respect ?? [],
  };
}

function checklistDefaults(review: ReviewData | null) {
  return checklistKeys.reduce<Record<string, boolean>>(
    (result, key) => ({
      ...result,
      [key]: review?.checklistAnswers[key] ?? false,
    }),
    {},
  );
}

function findingComplete(finding: ReviewFinding) {
  const highRisk = ["HIGH", "CRITICAL"].includes(finding.severity);
  return (
    finding.evidenceMediaIds.length > 0 &&
    finding.title.trim().length >= 5 &&
    finding.description.trim().length >= 20 &&
    (!highRisk || finding.action === "ESCALATE")
  );
}

function buildDraft(
  values: ScorecardValues,
  criterionEvidence: CriterionEvidence,
  findings: ReviewFinding[],
  checklistAnswers: Record<string, boolean>,
): ReviewDraft {
  return { ...values, criterionEvidence, findings, checklistAnswers };
}

function complete(
  values: ScorecardValues,
  criterionEvidence: CriterionEvidence,
  findings: ReviewFinding[],
  checklistAnswers: Record<string, boolean>,
) {
  const feedbackRequired = ["SUPPLEMENT", "REJECT"].includes(
    values.recommendation ?? "",
  );
  return (
    criteria.every(
      ({ key, scoreKey }) =>
        values[scoreKey] !== null &&
        values.criterionComments[key].trim().length > 0 &&
        criterionEvidence[key].length > 0,
    ) &&
    values.recommendation !== null &&
    checklistKeys.every((key) => checklistAnswers[key] === true) &&
    findings.every(findingComplete) &&
    (!feedbackRequired ||
      (values.applicantFeedback?.trim().length ?? 0) >= 50) &&
    (values.recommendation !== "SUPPLEMENT" ||
      findings.some((finding) => finding.action === "SUPPLEMENT"))
  );
}

export function FiveTScorecard({
  evidences,
  initialReview,
  isSaving,
  isSubmitting,
  onSave,
  onSubmit,
  readOnly,
}: {
  evidences: ReviewEvidenceSnapshot[];
  initialReview: ReviewData | null;
  isSaving: boolean;
  isSubmitting: boolean;
  onSave: (draft: ReviewDraft) => Promise<void>;
  onSubmit: () => Promise<void>;
  readOnly: boolean;
}) {
  const initialValues = useMemo(() => defaults(initialReview), [initialReview]);
  const [criterionEvidence, setCriterionEvidence] = useState<CriterionEvidence>(
    () => evidenceDefaults(initialReview),
  );
  const [findings, setFindings] = useState<ReviewFinding[]>(
    () => initialReview?.findings ?? [],
  );
  const [checklistAnswers, setChecklistAnswers] = useState<
    Record<string, boolean>
  >(() => checklistDefaults(initialReview));
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [completionError, setCompletionError] = useState("");
  const lastSaved = useRef(
    JSON.stringify(
      buildDraft(
        initialValues,
        evidenceDefaults(initialReview),
        initialReview?.findings ?? [],
        checklistDefaults(initialReview),
      ),
    ),
  );
  const saving = useRef(false);
  const queuedDraft = useRef<ReviewDraft | null>(null);
  const {
    control,
    formState: { errors, isDirty },
    getValues,
    register,
    trigger,
  } = useForm<ScorecardValues>({
    defaultValues: initialValues,
    resolver: zodResolver(draftSchema),
    mode: "onBlur",
  });
  const values = useWatch({ control });

  const persistDraft = useCallback(
    async (draft: ReviewDraft) => {
      if (saving.current) {
        queuedDraft.current = draft;
        return;
      }
      saving.current = true;
      let pending: ReviewDraft | null = draft;
      try {
        while (pending !== null) {
          queuedDraft.current = null;
          await onSave(pending);
          lastSaved.current = JSON.stringify(pending);
          pending = queuedDraft.current;
        }
      } catch {
        // A later field change will retry; never leave a rejected autosave promise.
        queuedDraft.current = null;
      } finally {
        saving.current = false;
      }
    },
    [onSave],
  );

  useEffect(() => {
    if (readOnly) return;
    const parsed = draftSchema.safeParse(values);
    if (!parsed.success || !findings.every(findingComplete)) return;
    const draft = buildDraft(
      parsed.data,
      criterionEvidence,
      findings,
      checklistAnswers,
    );
    if (JSON.stringify(draft) === lastSaved.current) return;
    const timer = window.setTimeout(() => void persistDraft(draft), 650);
    return () => window.clearTimeout(timer);
  }, [
    checklistAnswers,
    criterionEvidence,
    findings,
    isDirty,
    persistDraft,
    readOnly,
    values,
  ]);

  const current = draftSchema.safeParse(values);
  const total = current.success
    ? criteria.reduce(
        (sum, { scoreKey }) => sum + (current.data[scoreKey] ?? 0),
        0,
      )
    : 0;

  async function prepareSubmit() {
    const valid = await trigger();
    const parsed = draftSchema.safeParse(getValues());
    if (
      !valid ||
      !parsed.success ||
      !complete(parsed.data, criterionEvidence, findings, checklistAnswers)
    ) {
      setCompletionError(
        "Hoàn tất 5 điểm, nhận xét, bằng chứng, checklist và các phát hiện trước khi gửi.",
      );
      return;
    }
    const draft = buildDraft(
      parsed.data,
      criterionEvidence,
      findings,
      checklistAnswers,
    );
    try {
      // The submit endpoint intentionally only accepts an already persisted draft.
      // Save this exact validated snapshot before asking for final confirmation.
      saving.current = true;
      queuedDraft.current = null;
      await onSave(draft);
      lastSaved.current = JSON.stringify(draft);
      setCompletionError("");
      setConfirmOpen(true);
    } catch {
      setCompletionError(
        "Không thể lưu phiếu thẩm định trước khi gửi. Vui lòng thử lại.",
      );
    } finally {
      saving.current = false;
    }
  }

  return (
    <>
      <Card className="overflow-hidden">
        <div className="border-b bg-ink-950 px-6 py-6 text-white sm:px-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
                Khung đánh giá 5T
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight">
                Phiếu thẩm định chuyên môn
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                Mỗi kết luận cần có bằng chứng thuộc phiên bản hồ sơ đã khóa.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-right">
              <p className="text-xs text-slate-400">Tổng điểm tạm tính</p>
              <strong className="text-2xl text-gold-300">{total}/100</strong>
            </div>
          </div>
        </div>
        <form className="space-y-6 p-5 sm:p-8">
          {criteria.map(({ hint, key, label, scoreKey }, index) => (
            <fieldset
              className="grid gap-4 rounded-2xl border bg-neutral-50/70 p-4 sm:grid-cols-[minmax(0,1fr)_7rem] sm:p-5"
              disabled={readOnly}
              key={key}
            >
              <div>
                <legend className="font-bold text-neutral-950">
                  <span className="mr-2 text-primary-700">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {label}
                </legend>
                <p className="mt-1 text-xs leading-5 text-neutral-500">
                  {hint}
                </p>
                <label
                  className="mt-4 block text-xs font-bold uppercase tracking-wider text-neutral-600"
                  htmlFor={"comment-" + key}
                >
                  Nhận xét {label}
                </label>
                <textarea
                  className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3 text-sm disabled:bg-neutral-100"
                  id={"comment-" + key}
                  maxLength={2_000}
                  {...register(`criterionComments.${key}` as const)}
                />
                <ReviewEvidenceSelect
                  disabled={readOnly}
                  evidences={evidences}
                  label={label}
                  onChange={(next) =>
                    setCriterionEvidence((currentEvidence) => ({
                      ...currentEvidence,
                      [key]: next,
                    }))
                  }
                  value={criterionEvidence[key]}
                />
              </div>
              <div>
                <label
                  className="text-xs font-bold uppercase tracking-wider text-neutral-600"
                  htmlFor={"score-" + key}
                >
                  Điểm {label}
                </label>
                <input
                  className="mt-2 h-14 w-full rounded-xl border bg-white px-3 text-center text-2xl font-bold tabular-nums disabled:bg-neutral-100"
                  id={"score-" + key}
                  inputMode="numeric"
                  max={20}
                  min={0}
                  type="number"
                  {...register(scoreKey, {
                    setValueAs: (value) =>
                      value === "" ? null : Number(value),
                  })}
                />
                {errors[scoreKey]?.message ? (
                  <p className="mt-2 text-xs font-semibold text-red-700">
                    {errors[scoreKey]?.message}
                  </p>
                ) : null}
              </div>
            </fieldset>
          ))}

          <ReviewFindingsEditor
            disabled={readOnly}
            evidences={evidences}
            onChange={setFindings}
            value={findings}
          />

          <div className="grid gap-5 rounded-2xl border p-5 md:grid-cols-2">
            <div>
              <label className="text-sm font-bold" htmlFor="recommendation">
                Kiến nghị
              </label>
              <select
                className="mt-2 min-h-12 w-full rounded-xl border bg-white px-3 text-sm font-semibold disabled:bg-neutral-100"
                disabled={readOnly}
                id="recommendation"
                {...register("recommendation", {
                  setValueAs: (value) => value || null,
                })}
              >
                <option value="">Chọn kiến nghị</option>
                <option value="APPROVE">Đề nghị phê duyệt</option>
                <option value="SUPPLEMENT">Yêu cầu bổ sung</option>
                <option value="REJECT">Đề nghị từ chối</option>
              </select>
              <p className="mt-2 text-xs leading-5 text-neutral-500">
                Đây là kiến nghị chuyên môn, không phải quyết định cuối cùng.
              </p>
            </div>
            <div>
              <label className="text-sm font-bold" htmlFor="applicant-feedback">
                Phản hồi gửi người nộp
              </label>
              <textarea
                className="mt-2 min-h-28 w-full rounded-xl border bg-white p-3 text-sm disabled:bg-neutral-100"
                disabled={readOnly}
                id="applicant-feedback"
                maxLength={2_000}
                {...register("applicantFeedback", {
                  setValueAs: (value) => value || null,
                })}
              />
              <p className="mt-2 text-xs leading-5 text-neutral-500">
                Bắt buộc từ 50 ký tự khi yêu cầu bổ sung hoặc đề nghị từ chối.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className="text-sm font-bold" htmlFor="private-note">
                Ghi chú nội bộ
              </label>
              <textarea
                className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3 text-sm disabled:bg-neutral-100"
                disabled={readOnly}
                id="private-note"
                maxLength={5_000}
                {...register("privateNote", {
                  setValueAs: (value) => value || null,
                })}
              />
            </div>
          </div>

          <ReviewCompletionChecklist
            disabled={readOnly}
            onChange={(key, checked) =>
              setChecklistAnswers((currentAnswers) => ({
                ...currentAnswers,
                [key]: checked,
              }))
            }
            value={checklistAnswers}
          />

          {completionError ? (
            <p className="text-sm font-semibold text-red-700" role="alert">
              {completionError}
            </p>
          ) : null}
          {!findings.every(findingComplete) ? (
            <p className="text-sm font-semibold text-amber-800" role="status">
              Hoàn tất từng phát hiện để hệ thống có thể lưu phiếu nháp.
            </p>
          ) : null}
          <div className="flex flex-col justify-between gap-4 border-t pt-5 sm:flex-row sm:items-center">
            <p
              aria-live="polite"
              className="flex items-center gap-2 text-xs font-semibold text-neutral-500"
            >
              {readOnly ? (
                <>
                  <CheckCircle2 className="size-4 text-emerald-600" />
                  Kết quả đã gửi và không thể chỉnh sửa.
                </>
              ) : isSaving ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" />
                  Đang tự động lưu…
                </>
              ) : (
                <>
                  <Save className="size-4 text-emerald-600" />
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
                <Send aria-hidden="true" className="size-4" />
                Gửi kết quả thẩm định
              </Button>
            ) : null}
          </div>
        </form>
      </Card>
      <ConfirmationDialog
        confirmLabel="Xác nhận gửi"
        description="Sau khi gửi, phiếu thẩm định cùng các bằng chứng dẫn chiếu sẽ được khóa và không thể chỉnh sửa."
        isPending={isSubmitting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          void onSubmit()
            .then(() => setConfirmOpen(false))
            .catch(() => undefined);
        }}
        open={confirmOpen}
        title="Xác nhận gửi kết quả"
      />
    </>
  );
}
