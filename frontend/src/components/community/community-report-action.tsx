"use client";

import { useMutation } from "@tanstack/react-query";
import { Flag, Send } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { communityReportApi } from "@/lib/api/client";
import type {
  CommunityReportReason,
  CommunityTargetType,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const reasons: { value: CommunityReportReason; label: string }[] = [
  { value: "SPAM", label: "Nội dung rác hoặc quảng cáo" },
  { value: "HARASSMENT", label: "Quấy rối hoặc công kích" },
  { value: "HATE_SPEECH", label: "Ngôn từ thù ghét" },
  { value: "MISINFORMATION", label: "Thông tin sai lệch" },
  { value: "COPYRIGHT", label: "Vi phạm bản quyền" },
  { value: "ADVERTISING", label: "Quảng cáo không phù hợp" },
  { value: "PRIVACY_VIOLATION", label: "Xâm phạm quyền riêng tư" },
  { value: "OTHER", label: "Lý do khác" },
];

export function CommunityReportAction({
  targetId,
  targetLabel,
  targetType,
}: {
  targetId: string;
  targetLabel: string;
  targetType: CommunityTargetType;
}) {
  const user = useAuthUser();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<CommunityReportReason | "">("");
  const [details, setDetails] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const report = useMutation({
    mutationFn: () => {
      const input = {
        reason: reason as CommunityReportReason,
        ...(details.trim() ? { details: details.trim() } : {}),
      };
      return targetType === "POST"
        ? communityReportApi.reportPost(targetId, input)
        : communityReportApi.reportComment(targetId, input);
    },
    onSuccess: () => {
      setSubmitted(true);
      setOpen(false);
      setReason("");
      setDetails("");
    },
  });
  const actionName =
    targetType === "POST" ? "Báo cáo bài viết" : "Báo cáo bình luận";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason || report.isPending) return;
    report.mutate();
  }

  if (!user) {
    return (
      <Link className={actionClass} href="/login" title={targetLabel}>
        Đăng nhập để báo cáo
      </Link>
    );
  }

  return (
    <div className="inline-flex flex-col items-start">
      {submitted ? (
        <p
          aria-live="polite"
          className="text-sm font-semibold text-[var(--theme-accent)]"
          role="status"
        >
          Đã gửi báo cáo. Cảm ơn bạn đã giúp cộng đồng an toàn hơn.
        </p>
      ) : null}
      {!submitted ? (
        <button
          aria-controls={`community-report-form-${targetType.toLowerCase()}-${targetId}`}
          aria-expanded={open}
          aria-label={actionName}
          className={actionClass}
          onClick={() => setOpen((current) => !current)}
          title={targetLabel}
          type="button"
        >
          <Flag aria-hidden="true" className="size-4" /> {actionName}
        </button>
      ) : null}
      {open ? (
        <form
          className="mt-3 w-full max-w-xl rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
          id={`community-report-form-${targetType.toLowerCase()}-${targetId}`}
          onSubmit={submit}
        >
          <label
            className="block text-sm font-semibold text-[var(--theme-text)]"
            htmlFor={`community-report-reason-${targetId}`}
          >
            Lý do báo cáo
          </label>
          <select
            className={inputClass}
            id={`community-report-reason-${targetId}`}
            onChange={(event) =>
              setReason(event.target.value as CommunityReportReason | "")
            }
            required
            value={reason}
          >
            <option value="">Chọn lý do</option>
            {reasons.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <label
            className="mt-3 block text-sm font-semibold text-[var(--theme-text)]"
            htmlFor={`community-report-details-${targetId}`}
          >
            Chi tiết bổ sung (không bắt buộc)
          </label>
          <textarea
            className={inputClass}
            id={`community-report-details-${targetId}`}
            maxLength={2000}
            onChange={(event) => setDetails(event.target.value)}
            value={details}
          />
          {report.isError ? (
            <p className="mt-3 text-sm font-semibold text-red-700" role="alert">
              Chưa thể gửi báo cáo. Vui lòng kiểm tra kết nối rồi thử lại.
            </p>
          ) : null}
          <div className="mt-3 flex justify-end gap-2">
            <button
              className={secondaryClass}
              onClick={() => setOpen(false)}
              type="button"
            >
              Hủy
            </button>
            <button
              className={submitClass}
              disabled={!reason || report.isPending}
              type="submit"
            >
              <Send aria-hidden="true" className="size-4" /> Gửi báo cáo
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}

const actionClass =
  "inline-flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
const inputClass =
  "mt-2 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const submitClass =
  "inline-flex min-h-10 items-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50";
const secondaryClass =
  "inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-semibold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
