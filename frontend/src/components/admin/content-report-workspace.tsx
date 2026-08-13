"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ExternalLink,
  Flag,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { contentReportAdminApi } from "@/lib/api/client";
import type { ContentReportAdmin, ContentReportStatus } from "@/lib/api/types";

const statuses: Array<{ value: "" | ContentReportStatus; label: string }> = [
  { value: "", label: "Tất cả" },
  { value: "OPEN", label: "Mới" },
  { value: "UNDER_REVIEW", label: "Đang xử lý" },
  { value: "RESOLVED", label: "Đã giải quyết" },
  { value: "DISMISSED", label: "Đã bác bỏ" },
  { value: "SUSPENDED", label: "Đã tạm ngưng" },
];

export function ContentReportWorkspace() {
  const client = useQueryClient();
  const [status, setStatus] = useState<"" | ContentReportStatus>("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const reports = useQuery({
    queryKey: ["admin-content-reports", status],
    queryFn: () => contentReportAdminApi.list(status || undefined),
  });
  const transition = useMutation({
    mutationFn: ({
      report,
      next,
    }: {
      report: ContentReportAdmin;
      next: ContentReportStatus;
    }) =>
      next === "SUSPENDED"
        ? contentReportAdminApi.suspend(report, note.trim())
        : contentReportAdminApi.transition(
            report.id,
            next,
            next === "UNDER_REVIEW" ? null : note.trim(),
          ),
    onSuccess: async () => {
      setActiveId(null);
      setNote("");
      await client.invalidateQueries({ queryKey: ["admin-content-reports"] });
    },
  });

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header className="grid gap-6 border-b border-neutral-200 pb-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="flex items-center gap-2 text-sm font-bold text-primary-700">
            <Flag className="size-4" /> Trust &amp; Safety
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Hàng đợi báo cáo nội dung
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
            Tiếp nhận, phân loại và xử lý phản ánh công khai. Thông tin liên hệ
            được mã hóa và không hiển thị trong hàng đợi.
          </p>
        </div>
        <label className="text-sm font-semibold text-neutral-700">
          Trạng thái
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-4 lg:w-52"
            onChange={(event) =>
              setStatus(event.target.value as "" | ContentReportStatus)
            }
            value={status}
          >
            {statuses.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      {reports.isPending ? <ReportSkeleton /> : null}
      {reports.isError ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
          <AlertTriangle className="size-6" />
          <p className="mt-2 font-bold">Không thể tải hàng đợi báo cáo.</p>
          <Button
            className="mt-4"
            onClick={() => reports.refetch()}
            variant="outline"
          >
            <RefreshCcw className="size-4" /> Thử lại
          </Button>
        </div>
      ) : null}
      {reports.data?.data.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-neutral-300 bg-white p-12 text-center">
          <ShieldCheck className="mx-auto size-9 text-emerald-600" />
          <h2 className="mt-4 text-xl font-bold">
            Không có báo cáo trong trạng thái này
          </h2>
          <p className="mt-2 text-sm text-neutral-500">
            Hàng đợi hiện đã được xử lý sạch.
          </p>
        </div>
      ) : null}
      <div className="grid gap-4">
        {reports.data?.data.map((report) => (
          <article
            className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"
            key={report.id}
          >
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={report.status} />
                  <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-600">
                    {report.reason}
                  </span>
                  <span className="text-xs text-neutral-400">
                    {report.reporterType === "USER" ? "Tài khoản" : "Ẩn danh"}
                    {report.hasContactEmail ? " · Có email mã hóa" : ""}
                  </span>
                </div>
                <h2 className="mt-4 text-xl font-bold text-neutral-950">
                  {report.workTitle}
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
                  {report.description || "Không có mô tả bổ sung."}
                </p>
                <Link
                  className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-primary-700"
                  href={`/works/${report.workSlug}`}
                  target="_blank"
                >
                  Mở nội dung công khai <ExternalLink className="size-4" />
                </Link>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {report.status === "OPEN" ? (
                  <Button
                    onClick={() =>
                      transition.mutate({ report, next: "UNDER_REVIEW" })
                    }
                  >
                    Nhận xử lý
                  </Button>
                ) : null}
                {report.status === "UNDER_REVIEW" ? (
                  <Button
                    onClick={() =>
                      setActiveId(activeId === report.id ? null : report.id)
                    }
                    variant="outline"
                  >
                    Ra quyết định
                  </Button>
                ) : null}
              </div>
            </div>
            {activeId === report.id ? (
              <div className="mt-5 border-t border-neutral-200 pt-5">
                <label className="text-sm font-semibold text-neutral-700">
                  Ghi chú xử lý <span className="text-primary-700">*</span>
                  <textarea
                    className="mt-2 min-h-24 w-full rounded-xl border border-neutral-300 p-3"
                    maxLength={2000}
                    onChange={(event) => setNote(event.target.value)}
                    value={note}
                  />
                </label>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    disabled={!note.trim() || transition.isPending}
                    onClick={() =>
                      transition.mutate({ report, next: "RESOLVED" })
                    }
                  >
                    Đã giải quyết
                  </Button>
                  <Button
                    disabled={!note.trim() || transition.isPending}
                    onClick={() =>
                      transition.mutate({ report, next: "DISMISSED" })
                    }
                    variant="outline"
                  >
                    Bác bỏ
                  </Button>
                  <Button
                    className="border-red-300 text-red-700 hover:bg-red-50"
                    disabled={!note.trim() || transition.isPending}
                    onClick={() =>
                      transition.mutate({ report, next: "SUSPENDED" })
                    }
                    variant="outline"
                  >
                    Tạm ngưng tác phẩm
                  </Button>
                </div>
                {transition.isError ? (
                  <p className="mt-3 text-sm text-red-700" role="alert">
                    Không thể cập nhật. Tác phẩm hoặc báo cáo có thể đã thay
                    đổi.
                  </p>
                ) : null}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ContentReportStatus }) {
  const label = statuses.find((item) => item.value === status)?.label ?? status;
  return (
    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">
      {label}
    </span>
  );
}

function ReportSkeleton() {
  return (
    <div aria-label="Đang tải báo cáo" className="grid animate-pulse gap-4">
      <div className="h-40 rounded-2xl bg-neutral-200" />
      <div className="h-40 rounded-2xl bg-neutral-200" />
    </div>
  );
}
