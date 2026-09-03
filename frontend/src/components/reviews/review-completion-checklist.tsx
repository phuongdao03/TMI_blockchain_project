"use client";

import { ShieldCheck } from "lucide-react";

const items = [
  [
    "evidence_reviewed",
    "Đã kiểm tra đầy đủ bằng chứng thuộc phiên bản hồ sơ đã khóa.",
  ],
  [
    "criteria_assessed",
    "Đã hoàn tất mọi tiêu chí trong rubric được chỉ định cho loại hồ sơ này.",
  ],
  [
    "findings_recorded",
    "Đã ghi nhận đầy đủ phát hiện hoặc xác nhận không có phát hiện cần xử lý.",
  ],
  [
    "attestation",
    "Tôi chịu trách nhiệm về nội dung và căn cứ của phiếu thẩm định này.",
  ],
] as const;

export type ReviewChecklistKey = (typeof items)[number][0];

export function ReviewCompletionChecklist({
  disabled,
  onChange,
  value,
}: {
  disabled: boolean;
  onChange: (key: ReviewChecklistKey, checked: boolean) => void;
  value: Record<string, boolean>;
}) {
  return (
    <section className="rounded-2xl border border-primary-300/60 bg-[var(--theme-elevated)] p-5">
      <div className="flex gap-3">
        <ShieldCheck
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-primary-700"
        />
        <div>
          <h3 className="font-bold text-neutral-950">
            Checklist trước khi gửi
          </h3>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Các xác nhận này được lưu cùng phiếu thẩm định và không thể sửa sau
            khi gửi.
          </p>
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {items.map(([key, label]) => (
          <label
            className="flex cursor-pointer items-start gap-3 text-sm text-neutral-800"
            key={key}
          >
            <input
              checked={value[key] === true}
              className="mt-0.5 size-4 accent-primary-700"
              disabled={disabled}
              onChange={(event) => onChange(key, event.target.checked)}
              type="checkbox"
            />
            <span>{label}</span>
          </label>
        ))}
      </div>
    </section>
  );
}
