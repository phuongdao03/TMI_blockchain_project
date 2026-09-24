"use client";

import { useMutation } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { ApiError } from "@/lib/api/client";
import { saveWorkbook } from "@/lib/download";

export function HrReportDownload({
  download,
  filename,
  errorMessage,
}: {
  download: () => Promise<Blob>;
  filename: string;
  errorMessage: string;
}) {
  const exportReport = useMutation({
    mutationFn: download,
    onSuccess: (blob) => saveWorkbook(blob, filename),
  });

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-neutral-600">
        Báo cáo Excel sử dụng bộ lọc đang áp dụng.
      </p>
      <button
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-900 transition hover:bg-neutral-50 disabled:cursor-wait disabled:opacity-60"
        disabled={exportReport.isPending}
        onClick={() => exportReport.mutate()}
        type="button"
      >
        <Download className="size-4" aria-hidden="true" />
        {exportReport.isPending ? "Đang tạo báo cáo..." : "Xuất Excel"}
      </button>
      {exportReport.isError ? (
        <p className="w-full text-sm text-red-700" role="alert">
          {exportReport.error instanceof ApiError
            ? exportReport.error.message
            : errorMessage}
        </p>
      ) : null}
    </div>
  );
}
