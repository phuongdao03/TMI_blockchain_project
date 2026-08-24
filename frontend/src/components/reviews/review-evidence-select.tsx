"use client";

import { FileCheck2 } from "lucide-react";

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
    <fieldset className="mt-4">
      <legend className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-600">
        <FileCheck2 aria-hidden="true" className="size-4 text-primary-700" />
        Bằng chứng căn cứ cho {label}
      </legend>
      <p className="mt-1 text-xs leading-5 text-neutral-500">
        Chọn ít nhất một tài liệu thuộc phiên bản hồ sơ đã khóa.
      </p>
      <div className="mt-3 space-y-2">
        {evidences.map((evidence) => {
          const inputId = `${label}-${evidence.mediaAssetId}`;
          const checked = value.includes(evidence.mediaAssetId);
          return (
            <label
              className="flex cursor-pointer items-start gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2.5 text-sm transition hover:border-primary-300 has-[:checked]:border-primary-400 has-[:checked]:bg-primary-50/60"
              htmlFor={inputId}
              key={evidence.mediaAssetId}
            >
              <input
                checked={checked}
                className="mt-0.5 size-4 accent-primary-700"
                disabled={disabled}
                id={inputId}
                onChange={() => onChange(toggle(value, evidence.mediaAssetId))}
                type="checkbox"
              />
              <span className="min-w-0">
                <span className="block font-semibold text-neutral-900">
                  {evidence.title}
                </span>
                <span className="mt-0.5 block text-xs text-neutral-500">
                  {evidence.evidenceType}
                  {evidence.issuedAt ? ` · ${evidence.issuedAt}` : ""}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
