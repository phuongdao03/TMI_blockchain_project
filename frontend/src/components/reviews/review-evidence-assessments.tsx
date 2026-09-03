"use client";

import { FileCheck2 } from "lucide-react";

import { formatEvidenceMimeType } from "@/components/reviews/review-evidence-format";
import type {
  EvidenceAssessment,
  EvidenceAssessmentStatus,
  ReviewEvidenceSnapshot,
} from "@/lib/api/types";

const statusOptions: Array<{
  value: EvidenceAssessmentStatus;
  label: string;
}> = [
  { value: "UNREVIEWED", label: "Chưa kiểm tra" },
  { value: "VALID", label: "Phù hợp" },
  { value: "NEEDS_CLARIFICATION", label: "Cần làm rõ" },
  { value: "NOT_RELEVANT", label: "Không liên quan" },
];

export function ReviewEvidenceAssessments({
  assessments,
  evidences,
  onChange,
  readOnly = false,
}: {
  assessments: Record<string, EvidenceAssessment>;
  evidences: ReviewEvidenceSnapshot[];
  onChange: (value: Record<string, EvidenceAssessment>) => void;
  readOnly?: boolean;
}) {
  const update = (mediaId: string, value: EvidenceAssessment) => {
    onChange({ ...assessments, [mediaId]: value });
  };

  return (
    <section
      aria-labelledby="evidence-assessment-title"
      className="rounded-2xl border border-[var(--theme-border)]"
    >
      <div className="border-b border-[var(--theme-border)] p-4 sm:p-5">
        <h3
          className="flex items-center gap-2 font-bold"
          id="evidence-assessment-title"
        >
          <FileCheck2 aria-hidden="true" className="size-5 text-primary-700" />
          Kết quả kiểm tra từng tệp
        </h3>
        <p className="mt-1 text-sm text-neutral-600">
          Ghi nhận tệp phù hợp, cần làm rõ hoặc không liên quan.
        </p>
      </div>
      <div className="divide-y divide-[var(--theme-border)]">
        {evidences.map((evidence) => {
          const assessment = assessments[evidence.mediaAssetId] ?? {
            status: "UNREVIEWED" as const,
            note: "",
          };
          return (
            <article className="grid gap-3 p-4 sm:p-5" key={evidence.id}>
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_13rem] sm:items-center">
                <div className="min-w-0">
                  <p className="truncate font-semibold">{evidence.title}</p>
                  <p className="mt-1 text-xs text-neutral-500">
                    Định dạng {formatEvidenceMimeType(evidence.media.mimeType)}
                  </p>
                </div>
                <label className="text-sm font-semibold">
                  <span className="sr-only">
                    Kết quả kiểm tra {evidence.title}
                  </span>
                  <select
                    aria-label={`Kết quả kiểm tra ${evidence.title}`}
                    className="min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
                    disabled={readOnly}
                    onChange={(event) =>
                      update(evidence.mediaAssetId, {
                        ...assessment,
                        status: event.target.value as EvidenceAssessmentStatus,
                      })
                    }
                    value={assessment.status}
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {assessment.status === "NEEDS_CLARIFICATION" ? (
                <label className="text-sm font-semibold">
                  Nội dung cần khách hàng làm rõ
                  <textarea
                    className="mt-2 min-h-24 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 font-normal"
                    disabled={readOnly}
                    maxLength={1_000}
                    onChange={(event) =>
                      update(evidence.mediaAssetId, {
                        ...assessment,
                        note: event.target.value,
                      })
                    }
                    value={assessment.note}
                  />
                </label>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
