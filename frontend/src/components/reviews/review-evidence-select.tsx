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
      className="mt-4"
      role="group"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <p className="text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
          Tài liệu làm căn cứ
        </p>
        <p className="text-xs leading-5 text-[var(--theme-muted)]">
          Chọn ít nhất một tệp đã khóa.
        </p>
      </div>
      <div className="mt-2 grid gap-x-6 gap-y-1 md:grid-cols-2">
        {evidences.map((evidence) => {
          const checked = value.includes(evidence.mediaAssetId);
          return (
            <label
              className="grid min-h-12 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-lg py-1.5 text-sm transition-colors hover:text-[var(--theme-accent)] has-[:checked]:text-[var(--theme-accent)]"
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
