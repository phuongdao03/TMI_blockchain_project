"use client";

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
        <p className="text-xs font-bold uppercase tracking-wider text-neutral-600">
          Tài liệu làm căn cứ
        </p>
        <p className="text-xs leading-5 text-neutral-500">
          Chọn ít nhất một tệp đã khóa.
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {evidences.map((evidence) => {
          const inputId = `${label}-${evidence.mediaAssetId}`;
          const checked = value.includes(evidence.mediaAssetId);
          return (
            <label
              className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm transition-colors duration-150 hover:border-primary-400 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 has-[:checked]:text-primary-900"
              htmlFor={inputId}
              key={evidence.mediaAssetId}
            >
              <input
                checked={checked}
                className="size-4 accent-primary-700"
                disabled={disabled}
                id={inputId}
                onChange={() => onChange(toggle(value, evidence.mediaAssetId))}
                type="checkbox"
              />
              <span className="max-w-72 truncate font-semibold">
                {evidence.title}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
