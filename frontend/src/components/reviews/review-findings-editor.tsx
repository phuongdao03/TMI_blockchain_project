"use client";

import { AlertTriangle, Plus, Trash2 } from "lucide-react";

import type {
  ReviewEvidenceSnapshot,
  ReviewFinding,
  ReviewFindingAction,
  ReviewFindingSeverity,
} from "@/lib/api/types";

const criteria = [
  ["truth", "Tính đúng đắn"],
  ["transparency", "Tính minh bạch"],
  ["ownership", "Tinh thần trách nhiệm"],
  ["professionalism", "Tính chuyên nghiệp"],
  ["respect", "Sự tôn trọng"],
] as const;

const severityLabels: Record<ReviewFindingSeverity, string> = {
  INFO: "Thông tin",
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Nghiêm trọng",
};

const actionLabels: Record<ReviewFindingAction, string> = {
  NOTE: "Ghi nhận",
  SUPPLEMENT: "Yêu cầu bổ sung",
  ESCALATE: "Chuyển cấp xử lý",
};

function nextId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `00000000-0000-4000-8000-${Date.now().toString(16).padStart(12, "0").slice(-12)}`;
}

function toggle(values: string[], value: string) {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export function ReviewFindingsEditor({
  disabled,
  evidences,
  onChange,
  value,
}: {
  disabled: boolean;
  evidences: ReviewEvidenceSnapshot[];
  onChange: (findings: ReviewFinding[]) => void;
  value: ReviewFinding[];
}) {
  function update(index: number, patch: Partial<ReviewFinding>) {
    onChange(
      value.map((item, current) =>
        current === index ? { ...item, ...patch } : item,
      ),
    );
  }

  return (
    <section className="rounded-2xl border bg-white p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-amber-800">
            <AlertTriangle aria-hidden="true" className="size-4" />
            Phát hiện có căn cứ
          </p>
          <h3 className="mt-2 text-xl font-bold text-neutral-950">
            Rủi ro, thiếu sót và yêu cầu làm rõ
          </h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">
            Mỗi phát hiện phải gắn với tiêu chí 5T và bằng chứng trong phiên bản
            đã khóa.
          </p>
        </div>
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-primary-300 bg-white px-4 text-sm font-bold text-primary-800 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled}
          onClick={() =>
            onChange([
              ...value,
              {
                id: nextId(),
                severity: "MEDIUM",
                criterion: "truth",
                evidenceMediaIds: [],
                title: "",
                description: "",
                action: "NOTE",
              },
            ])
          }
          type="button"
        >
          <Plus aria-hidden="true" className="size-4" />
          Thêm phát hiện
        </button>
      </div>

      {value.length ? (
        <div className="mt-5 space-y-5">
          {value.map((finding, index) => {
            const forcedEscalation = ["HIGH", "CRITICAL"].includes(
              finding.severity,
            );
            return (
              <fieldset
                className="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4"
                key={finding.id}
              >
                <legend className="px-1 text-sm font-bold text-neutral-900">
                  Phát hiện {index + 1}
                </legend>
                <div className="grid gap-4 md:grid-cols-3">
                  <label className="text-sm font-bold text-neutral-800">
                    Mức độ
                    <select
                      className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3 font-medium"
                      disabled={disabled}
                      onChange={(event) => {
                        const severity = event.target
                          .value as ReviewFindingSeverity;
                        update(index, {
                          severity,
                          action: ["HIGH", "CRITICAL"].includes(severity)
                            ? "ESCALATE"
                            : finding.action,
                        });
                      }}
                      value={finding.severity}
                    >
                      {Object.entries(severityLabels).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm font-bold text-neutral-800">
                    Tiêu chí liên quan
                    <select
                      className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3 font-medium"
                      disabled={disabled}
                      onChange={(event) =>
                        update(index, {
                          criterion: event.target
                            .value as ReviewFinding["criterion"],
                        })
                      }
                      value={finding.criterion}
                    >
                      {criteria.map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm font-bold text-neutral-800">
                    Hướng xử lý
                    <select
                      className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3 font-medium disabled:bg-neutral-100"
                      disabled={disabled || forcedEscalation}
                      onChange={(event) =>
                        update(index, {
                          action: event.target.value as ReviewFindingAction,
                        })
                      }
                      value={finding.action}
                    >
                      {Object.entries(actionLabels).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="mt-4 block text-sm font-bold text-neutral-800">
                  Tóm tắt phát hiện
                  <input
                    className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3"
                    disabled={disabled}
                    maxLength={240}
                    onChange={(event) =>
                      update(index, { title: event.target.value })
                    }
                    value={finding.title}
                  />
                </label>
                <label className="mt-4 block text-sm font-bold text-neutral-800">
                  Phân tích và căn cứ
                  <textarea
                    className="mt-2 min-h-28 w-full rounded-xl border bg-white p-3"
                    disabled={disabled}
                    maxLength={2_000}
                    onChange={(event) =>
                      update(index, { description: event.target.value })
                    }
                    value={finding.description}
                  />
                </label>
                <fieldset className="mt-4">
                  <legend className="text-sm font-bold text-neutral-800">
                    Bằng chứng liên quan
                  </legend>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {evidences.map((evidence) => (
                      <label
                        className="flex cursor-pointer items-center gap-2 rounded-lg border bg-white p-2.5 text-sm"
                        key={evidence.mediaAssetId}
                      >
                        <input
                          checked={finding.evidenceMediaIds.includes(
                            evidence.mediaAssetId,
                          )}
                          className="size-4 accent-primary-700"
                          disabled={disabled}
                          onChange={() =>
                            update(index, {
                              evidenceMediaIds: toggle(
                                finding.evidenceMediaIds,
                                evidence.mediaAssetId,
                              ),
                            })
                          }
                          type="checkbox"
                        />
                        <span className="truncate">{evidence.title}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
                <button
                  className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-red-700 hover:text-red-900 disabled:opacity-50"
                  disabled={disabled}
                  onClick={() =>
                    onChange(value.filter((_, current) => current !== index))
                  }
                  type="button"
                >
                  <Trash2 aria-hidden="true" className="size-4" />
                  Xóa phát hiện
                </button>
              </fieldset>
            );
          })}
        </div>
      ) : (
        <p className="mt-5 rounded-xl border border-dashed bg-neutral-50 px-4 py-5 text-sm text-neutral-600">
          Chưa có phát hiện cần xử lý. Bạn vẫn phải xác nhận việc này trong
          checklist trước khi gửi.
        </p>
      )}
    </section>
  );
}
