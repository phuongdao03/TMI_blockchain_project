"use client";

import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, publicApi } from "@/lib/api/client";
import type { ContentReportReason, PublicWorkDetail } from "@/lib/api/types";

const reasons: Array<{ value: ContentReportReason; label: string }> = [
  { value: "COPYRIGHT", label: "Vi phạm bản quyền" },
  { value: "INCORRECT_INFORMATION", label: "Thông tin không chính xác" },
  { value: "INAPPROPRIATE_CONTENT", label: "Nội dung không phù hợp" },
  { value: "OTHER", label: "Lý do khác" },
];

export function PublicContentReportDialog({
  detail,
  onClose,
}: {
  detail: PublicWorkDetail;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [reason, setReason] = useState<ContentReportReason>("COPYRIGHT");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const submit = useMutation({
    mutationFn: () =>
      publicApi.reportWork(detail.id, {
        reason,
        description: description.trim() || null,
        reporterEmail: email.trim() || null,
      }),
  });

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
      previous?.focus();
    };
  }, [onClose]);

  return (
    <div
      aria-labelledby="content-report-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-ink-950/90 p-4 backdrop-blur-sm"
      role="dialog"
    >
      <div className="w-full max-w-xl rounded-3xl border border-white/15 bg-ink-900 p-6 shadow-2xl sm:p-8">
        <header className="flex items-start justify-between gap-5">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-primary-400 uppercase">
              Kiểm soát cộng đồng
            </p>
            <h2 className="mt-2 text-2xl font-bold text-white" id="content-report-title">
              Báo cáo nội dung
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Báo cáo “{detail.title}” sẽ được chuyển tới đội ngũ kiểm duyệt.
            </p>
          </div>
          <button
            aria-label="Đóng báo cáo"
            className="grid size-11 shrink-0 place-items-center rounded-full border border-white/15 text-slate-300 hover:bg-white/10"
            onClick={onClose}
            ref={closeRef}
            type="button"
          >
            <X className="size-5" />
          </button>
        </header>

        {submit.isSuccess ? (
          <div className="mt-8 rounded-2xl border border-emerald-400/25 bg-emerald-400/5 p-5">
            <CheckCircle2 className="size-7 text-emerald-300" />
            <h3 className="mt-3 font-bold text-white">Đã tiếp nhận báo cáo</h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Mã báo cáo: <span className="font-mono">{submit.data.id}</span>. Danh tính người báo cáo không được hiển thị công khai.
            </p>
            <Button className="mt-5" onClick={onClose} type="button">
              Hoàn tất
            </Button>
          </div>
        ) : (
          <form
            className="mt-7 space-y-5"
            onSubmit={(event) => {
              event.preventDefault();
              submit.mutate();
            }}
          >
            <label className="block text-sm font-semibold text-slate-200">
              Lý do <span className="text-primary-400">*</span>
              <select
                className="mt-2 min-h-12 w-full rounded-xl border border-white/15 bg-ink-950 px-4 text-white outline-none focus:border-gold-300"
                onChange={(event) => setReason(event.target.value as ContentReportReason)}
                value={reason}
              >
                {reasons.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold text-slate-200">
              Mô tả bổ sung
              <textarea
                className="mt-2 min-h-28 w-full rounded-xl border border-white/15 bg-ink-950 p-4 text-white outline-none focus:border-gold-300"
                maxLength={2000}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Cung cấp thông tin giúp đội ngũ xác minh báo cáo."
                value={description}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-200">
              Email liên hệ (không bắt buộc)
              <input
                autoComplete="email"
                className="mt-2 min-h-12 w-full rounded-xl border border-white/15 bg-ink-950 px-4 text-white outline-none focus:border-gold-300"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="ban@example.vn"
                type="email"
                value={email}
              />
            </label>
            {submit.isError ? (
              <p className="flex items-start gap-2 text-sm text-red-300" role="alert">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                {submit.error instanceof ApiError && submit.error.code === "CONTENT_REPORT_DUPLICATE"
                  ? "Báo cáo tương tự đã được tiếp nhận trong hôm nay."
                  : "Chưa thể gửi báo cáo. Vui lòng kiểm tra thông tin và thử lại."}
              </p>
            ) : null}
            <Button className="w-full" disabled={submit.isPending} type="submit">
              <Send className="size-4" />
              {submit.isPending ? "Đang gửi…" : "Gửi báo cáo"}
            </Button>
            <p className="text-xs leading-5 text-slate-500">
              Hệ thống áp dụng giới hạn tần suất, chống trùng và có thể yêu cầu CAPTCHA theo mức rủi ro. Email được mã hóa và không xuất hiện trên trang công khai.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
