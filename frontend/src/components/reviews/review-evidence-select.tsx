"use client";

import { formatEvidenceMimeType } from "@/components/reviews/review-evidence-format";
import type { ReviewEvidenceSnapshot } from "@/lib/api/types";

function toggle(values: string[], value: string) {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export function ReviewEvidenceSelect({
  disabled,
  evidences,
  label,
  onChange,
  value,
}: {
  disabled: boolean;
  evidences: ReviewEvidenceSnapshot[];
  label: string;
  onChange: (values: string[]) => void;
  value: string[];
}) {
  if (!evidences.length) {
    return (
      <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber-900">
        Hồ sơ chưa có bằng chứng để dẫn chiếu. Hãy ghi nhận phát hiện và kiến
        nghị bổ sung trước khi gửi phiếu.
      </p>
    );
  }

  return (
    <div
      aria-label={`Bằng chứng căn cứ cho ${label}`}
      className="mt-3 rounded-xl bg-[var(--theme-elevated)] p-3 sm:p-4"
      role="group"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-bold text-[var(--theme-text)]">
          Tài liệu dẫn chiếu
        </p>
        <p className="text-xs leading-5 text-[var(--theme-muted)]">
          Chọn tệp làm căn cứ cho tiêu chí này
        </p>
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {evidences.map((evidence) => {
          const checked = value.includes(evidence.mediaAssetId);
          return (
            <label
              className="grid min-h-11 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-lg border border-transparent bg-[var(--theme-surface)] px-3 py-2 text-sm transition-colors hover:border-[var(--theme-border)] has-[:checked]:border-[var(--theme-accent)] has-[:checked]:text-[var(--theme-accent)] has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[var(--theme-accent)]"
              key={evidence.mediaAssetId}
            >
              <input
                checked={checked}
                className="size-4 accent-primary-700"
                disabled={disabled}
                onChange={() => onChange(toggle(value, evidence.mediaAssetId))}
                type="checkbox"
              />
              <span className="min-w-0">
                <span className="block break-words font-semibold">
                  {evidence.title}
                </span>
                <span className="mt-0.5 block text-xs text-[var(--theme-muted)]">
                  Định dạng {formatEvidenceMimeType(evidence.media.mimeType)}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
