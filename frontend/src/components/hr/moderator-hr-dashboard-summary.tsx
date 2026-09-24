"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, RefreshCw } from "lucide-react";
import Link from "next/link";

import { hrModeratorDashboardApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import {
  attendancePresentation,
  formatUpdatedAt,
  formatWorksiteTime,
} from "./moderator-hr-presentation";

export function ModeratorHrDashboardSummary() {
  const user = useAuthUser();
  const summary = useQuery({
    queryKey: ["hr", "moderator-dashboard-summary", user?.id],
    queryFn: hrModeratorDashboardApi.summary,
    gcTime: 0,
  });

  if (summary.isPending) {
    return (
      <section aria-label="Đang tải tổng quan nhân sự cá nhân" role="status">
        <span className="sr-only">Đang tải tổng quan nhân sự cá nhân.</span>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }, (_, index) => (
            <span
              aria-hidden="true"
              className="h-32 animate-pulse rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
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
        aria-labelledby="moderator-hr-dashboard-title"
        className="rounded-xl border border-error/30 bg-[var(--theme-surface)] p-5"
        role="alert"
      >
        <h2
          className="font-bold text-[var(--theme-text)]"
          id="moderator-hr-dashboard-title"
        >
          Chưa tải được tổng quan nhân sự cá nhân
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
          {summary.isFetching ? "Đang tải lại" : "Thử tải lại"}
        </button>
      </section>
    );
  }

  if (!summary.data.profileLinked) {
    return (
      <section
        aria-labelledby="moderator-hr-dashboard-title"
        className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
      >
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.18em] text-[var(--theme-accent)]">
          Nhân sự cá nhân
        </p>
        <h2
          className="mt-2 text-2xl font-bold tracking-[-0.03em] text-[var(--theme-text)]"
          id="moderator-hr-dashboard-title"
        >
          Chưa liên kết hồ sơ nhân sự
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
          Super Admin cần liên kết hồ sơ nhân sự với tài khoản này trước khi bạn
          có thể sử dụng chấm công, nghỉ phép và tăng ca.
        </p>
      </section>
    );
  }

  const attendance = attendancePresentation(summary.data);
  const updatedAt = formatUpdatedAt(
    summary.data.updatedAt,
    summary.data.timezone,
  );
  return (
    <section
      aria-labelledby="moderator-hr-dashboard-title"
      className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 shadow-sm sm:p-6"
    >
      <div className="flex flex-col gap-3 border-b border-[var(--theme-border)] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.18em] text-[var(--theme-accent)]">
            Nhân sự cá nhân
          </p>
          <h2
            className="mt-2 text-2xl font-bold tracking-[-0.03em] text-[var(--theme-text)] sm:text-3xl"
            id="moderator-hr-dashboard-title"
          >
            Chấm công và yêu cầu cá nhân
          </h2>
          {summary.data.workDate && summary.data.timezone ? (
            <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
              Ngày làm việc {summary.data.workDate} theo {summary.data.timezone}
              .
            </p>
          ) : null}
        </div>
        {updatedAt ? (
          <div className="flex shrink-0 flex-col gap-2">
            <p className="text-xs text-[var(--theme-muted)]">
              Cập nhật lúc {updatedAt} ({summary.data.timezone ?? "UTC"})
            </p>
            <button
              type="button"
              disabled={summary.isFetching}
              onClick={() => void summary.refetch()}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)] disabled:opacity-60"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              {summary.isFetching
                ? "Đang cập nhật"
                : "Làm mới tổng quan cá nhân"}
            </button>
          </div>
        ) : null}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Link
          className="group min-w-0 min-h-32 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 transition-colors hover:border-[var(--theme-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-text)]"
          href="/attendance"
        >
          <p className="text-sm font-bold text-[var(--theme-text)]">
            {attendance.title}
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
            {attendance.description}
          </p>
          {summary.data.timezone && summary.data.attendanceStatus ? (
            <div className="mt-3 space-y-1 text-sm tabular-nums text-[var(--theme-text)]">
              <p>
                Giờ vào:{" "}
                {formatWorksiteTime(
                  summary.data.checkInAt,
                  summary.data.timezone,
                )}
              </p>
              <p>
                Giờ ra:{" "}
                {formatWorksiteTime(
                  summary.data.checkOutAt,
                  summary.data.timezone,
                )}
              </p>
            </div>
          ) : null}
          <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-[var(--theme-text)]">
            {attendance.actionLabel}
            <ArrowRight aria-hidden="true" className="size-4" />
          </span>
        </Link>
        <Link
          className="group min-w-0 min-h-32 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 transition-colors hover:border-[var(--theme-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-text)]"
          href="/leave"
        >
          <p className="text-3xl font-bold tracking-[-0.04em] text-[var(--theme-text)]">
            {summary.data.leavePendingCount}
          </p>
          <p className="mt-3 text-sm font-semibold text-[var(--theme-muted)]">
            Yêu cầu nghỉ phép đang chờ
          </p>
        </Link>
        <Link
          className="group min-w-0 min-h-32 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 transition-colors hover:border-[var(--theme-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-text)]"
          href="/overtime"
        >
          <p className="text-3xl font-bold tracking-[-0.04em] text-[var(--theme-text)]">
            {summary.data.overtimePendingCount}
          </p>
          <p className="mt-3 text-sm font-semibold text-[var(--theme-muted)]">
            Yêu cầu tăng ca đang chờ
          </p>
        </Link>
      </div>
    </section>
  );
}
