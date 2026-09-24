"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { RefreshCw } from "lucide-react";

import { hrDashboardApi } from "@/lib/api/client";
import type { HrDashboardSummary } from "@/lib/api/types";

type QueueCard = {
  href: string;
  label: string;
  value: (summary: HrDashboardSummary) => number;
};

const queueCards: readonly QueueCard[] = [
  {
    href: "/admin/employees",
    label: "Nhân viên đang hoạt động",
    value: (summary) => summary.activeEmployeeCount,
  },
  {
    href: "/admin/attendance",
    label: "Chấm công chờ duyệt",
    value: (summary) => summary.attendancePendingCount,
  },
  {
    href: "/admin/attendance",
    label: "Vị trí cần duyệt",
    value: (summary) => summary.locationExceptionPendingCount,
  },
  {
    href: "/admin/leave",
    label: "Nghỉ phép chờ duyệt",
    value: (summary) => summary.leavePendingCount,
  },
  {
    href: "/admin/overtime",
    label: "Tăng ca chờ duyệt",
    value: (summary) => summary.overtimePendingCount,
  },
  {
    href: "/admin/payroll",
    label: "Kỳ lương bản nháp",
    value: (summary) => summary.payrollDraftCount,
  },
];

function UpdatedAt({ value }: { value: string }) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return null;
  return (
    <p className="text-xs text-neutral-500">
      Cập nhật lúc{" "}
      {date.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" })}
    </p>
  );
}

export function HrDashboardSummary() {
  const summary = useQuery({
    queryKey: ["hr", "dashboard-summary"],
    queryFn: hrDashboardApi.summary,
    gcTime: 0,
  });

  if (summary.isPending) {
    return (
      <section
        aria-label="Đang tải hàng đợi nhân sự"
        className="mx-auto max-w-7xl"
        role="status"
      >
        <span className="sr-only">Đang tải hàng đợi nhân sự.</span>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <span
              aria-hidden="true"
              className="h-28 animate-pulse rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
              key={index}
            />
          ))}
        </div>
      </section>
    );
  }

  if (summary.isError || !summary.data) {
    return (
      <section
        aria-labelledby="hr-dashboard-summary-title"
        className="mx-auto max-w-7xl rounded-xl border border-error/30 bg-[var(--theme-surface)] p-5"
        role="alert"
      >
        <h2
          className="font-bold text-[var(--theme-text)]"
          id="hr-dashboard-summary-title"
        >
          Chưa tải được hàng đợi nhân sự
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
          Dữ liệu chưa bị thay đổi. Hãy thử kết nối lại với dịch vụ nhân sự.
        </p>
        <button
          className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white hover:bg-primary-800 disabled:opacity-60"
          disabled={summary.isFetching}
          onClick={() => void summary.refetch()}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={`size-4 ${summary.isFetching ? "animate-spin" : ""}`}
          />
          {summary.isFetching ? "Đang tải lại" : "Thử tải lại hàng đợi"}
        </button>
      </section>
    );
  }

  const totalPending = queueCards
    .slice(1)
    .reduce((total, card) => total + card.value(summary.data), 0);

  return (
    <section
      aria-labelledby="hr-dashboard-summary-title"
      className="mx-auto max-w-7xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 shadow-sm sm:p-6"
    >
      <div className="flex flex-col gap-3 border-b border-[var(--theme-border)] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.18em] text-primary-700">
            Điều hành nhân sự
          </p>
          <h2
            className="mt-2 text-2xl font-bold tracking-[-0.03em] text-[var(--theme-text)] sm:text-3xl"
            id="hr-dashboard-summary-title"
          >
            Hàng đợi cần xử lý
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
            Chỉ số tổng hợp để điều phối. Màn hình này không hiển thị vị trí, lý
            do yêu cầu hoặc dữ liệu lương cá nhân.
          </p>
        </div>
        <UpdatedAt value={summary.data.updatedAt} />
      </div>

      {totalPending === 0 ? (
        <p className="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900">
          Không có hàng đợi nhân sự cần xử lý.
        </p>
      ) : null}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {queueCards.map((card) => (
          <Link
            className="group min-h-28 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 transition-colors hover:border-primary-400 hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
            href={card.href}
            key={card.label}
          >
            <p className="text-3xl font-bold tracking-[-0.04em] text-[var(--theme-text)]">
              {card.value(summary.data)}
            </p>
            <p className="mt-3 text-sm font-semibold text-[var(--theme-muted)] group-hover:text-primary-800">
              {card.label}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
