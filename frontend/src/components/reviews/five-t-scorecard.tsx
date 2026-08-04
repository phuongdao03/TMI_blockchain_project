"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, LoaderCircle, Save, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import type { ReviewData, ReviewDraft } from "@/lib/api/types";

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
  recommendation: z.enum(["APPROVE", "SUPPLEMENT", "REJECT"]).nullable(),
  privateNote: z.string().max(5_000).nullable(),
});

type ScorecardValues = z.infer<typeof draftSchema>;
type ScoreKey = Exclude<
  keyof ScorecardValues,
  "criterionComments" | "recommendation" | "privateNote"
>;
type CriterionKey = keyof ScorecardValues["criterionComments"];

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
    hint: "Mức độ chính xác, xác thực và nhất quán của thông tin.",
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
    recommendation: review?.recommendation ?? null,
    privateNote: review?.privateNote ?? null,
  };
}

function isComplete(values: ScorecardValues) {
  return (
    criteria.every(
      ({ key, scoreKey }) =>
        values[scoreKey] !== null &&
        values.criterionComments[key].trim().length > 0,
    ) && values.recommendation !== null
  );
}

export function FiveTScorecard({
  initialReview,
  isSaving,
  isSubmitting,
  onSave,
  onSubmit,
  readOnly,
}: {
  initialReview: ReviewData | null;
  isSaving: boolean;
  isSubmitting: boolean;
  onSave: (draft: ReviewDraft) => Promise<void>;
  onSubmit: () => Promise<void>;
  readOnly: boolean;
}) {
  const initialValues = useMemo(() => defaults(initialReview), [initialReview]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [completionError, setCompletionError] = useState("");
  const lastSaved = useRef(JSON.stringify(initialValues));
  const saving = useRef(false);
  const queuedDraft = useRef<ScorecardValues | null>(null);
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
    async (draft: ScorecardValues) => {
      if (saving.current) {
        queuedDraft.current = draft;
        return;
      }
      saving.current = true;
      let current: ScorecardValues | null = draft;
      try {
        while (current !== null) {
          const pending = current;
          queuedDraft.current = null;
          await onSave(pending);
          lastSaved.current = JSON.stringify(pending);
          current = queuedDraft.current;
        }
      } catch {
        queuedDraft.current = null;
      } finally {
        saving.current = false;
      }
    },
    [onSave],
  );

  useEffect(() => {
    if (readOnly || !isDirty) return;
    const serialized = JSON.stringify(values);
    if (serialized === lastSaved.current) return;
    const timer = window.setTimeout(() => {
      const parsed = draftSchema.safeParse(getValues());
      if (!parsed.success) return;
      void persistDraft(parsed.data);
    }, 650);
    return () => window.clearTimeout(timer);
  }, [getValues, isDirty, persistDraft, readOnly, values]);

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
    if (!valid || !parsed.success || !isComplete(parsed.data)) {
      setCompletionError(
        "Hoàn thiện đủ 5 điểm, 5 nhận xét và kiến nghị trước khi gửi.",
      );
      return;
    }
    setCompletionError("");
    setConfirmOpen(true);
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
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-right">
              <p className="text-xs text-slate-400">Tổng điểm tạm tính</p>
              <strong className="text-2xl text-gold-300">{total}/100</strong>
            </div>
          </div>
        </div>
        <form className="space-y-5 p-5 sm:p-8">
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
                  htmlFor={`comment-${key}`}
                >
                  Nhận xét {label}
                </label>
                <textarea
                  className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3 text-sm disabled:bg-neutral-100"
                  id={`comment-${key}`}
                  maxLength={2_000}
                  {...register(`criterionComments.${key}`)}
                />
              </div>
              <div>
                <label
                  className="text-xs font-bold uppercase tracking-wider text-neutral-600"
                  htmlFor={`score-${key}`}
                >
                  Điểm {label}
                </label>
                <input
                  className="mt-2 h-14 w-full rounded-xl border bg-white px-3 text-center text-2xl font-bold tabular-nums disabled:bg-neutral-100"
                  id={`score-${key}`}
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
            </div>
            <div>
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

          {completionError ? (
            <p className="text-sm font-semibold text-red-700" role="alert">
              {completionError}
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
        description="Sau khi gửi, phiếu điểm sẽ được khóa và không thể chỉnh sửa. Hãy kiểm tra kỹ toàn bộ nội dung."
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
