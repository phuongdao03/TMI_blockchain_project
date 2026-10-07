"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarClock,
  ClipboardCheck,
  Inbox,
  LoaderCircle,
} from "lucide-react";
import Link from "next/link";

import { reviewApi } from "@/lib/api/client";
import type {
  ReviewAssignmentStatus,
  ReviewListFilters,
} from "@/lib/api/types";
import { reviewKeys } from "@/lib/reviews/query-keys";
import { cn } from "@/lib/utils";

const statusLabels: Record<ReviewAssignmentStatus, string> = {
  ASSIGNED: "Mới được giao",
  IN_PROGRESS: "Đang thẩm định",
  CONFLICTED: "Đã kết thúc",
  SUBMITTED: "Đã gửi kết quả",
  CANCELLED: "Đã hủy",
};

const statusClasses: Record<ReviewAssignmentStatus, string> = {
  ASSIGNED:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200",
  IN_PROGRESS:
    "border-primary-100 bg-primary-50 text-primary-700 dark:border-amber-700 dark:bg-[var(--theme-elevated)] dark:text-[var(--theme-accent)]",
  CONFLICTED:
    "border-red-200 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-950/40 dark:text-red-200",
  SUBMITTED:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200",
  CANCELLED:
    "border-neutral-200 bg-neutral-100 text-neutral-600 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200",
};

function formatDate(value: string | null) {
  if (!value) return "Không giới hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isActive(status: ReviewAssignmentStatus) {
  return status === "ASSIGNED" || status === "IN_PROGRESS";
}

export function ReviewAssignmentList({
  page,
  pageSize,
  status,
}: {
  page: number;
  pageSize: number;
  status?: ReviewAssignmentStatus;
}) {
  const filters: ReviewListFilters = { page, pageSize, status };
  const { data, dataUpdatedAt, error, isPending, isFetching, refetch } =
    useQuery({
      queryKey: reviewKeys.list(filters),
      queryFn: () => reviewApi.list(filters),
    });

  if (isPending) {
    return (
      <div
        className="grid min-h-64 place-items-center rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
        role="status"
      >
        <span className="flex items-center gap-3 text-sm font-semibold text-[var(--theme-muted)]">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang tải hàng đợi thẩm định…
        </span>
      </div>
    );
  }
  if (error) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800"
        role="alert"
      >
        <p>Không thể tải hàng đợi thẩm định. Vui lòng thử lại.</p>
        <button
          className="mt-3 min-h-11 rounded-lg border border-red-300 px-4"
          disabled={isFetching}
          onClick={() => void refetch()}
          type="button"
        >
          Thử tải lại
        </button>
      </div>
    );
  }
  if (!data?.data.length) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--theme-border)] bg-[var(--theme-surface)] px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary-50 text-primary-700">
          <Inbox aria-hidden="true" className="size-7" />
        </span>
        <h2 className="mt-5 text-xl font-bold">Không có hồ sơ phù hợp</h2>
        <p className="mt-2 text-sm text-[var(--theme-muted)]">
          Hàng đợi sẽ cập nhật khi bạn được phân công hồ sơ mới.
        </p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.meta.total / pageSize));
  const isOverdue = (status: ReviewAssignmentStatus, dueAt: string | null) =>
    isActive(status) &&
    dueAt !== null &&
    new Date(dueAt).getTime() < dataUpdatedAt;
  const orderedAssignments = [...data.data].sort((left, right) => {
    const priority = (status: ReviewAssignmentStatus, dueAt: string | null) =>
      isOverdue(status, dueAt) ? 0 : isActive(status) ? 1 : 2;
    const difference =
      priority(left.assignment.status, left.assignment.dueAt) -
      priority(right.assignment.status, right.assignment.dueAt);
    if (difference) return difference;
    return (
      (left.assignment.dueAt
        ? new Date(left.assignment.dueAt).getTime()
        : Number.POSITIVE_INFINITY) -
      (right.assignment.dueAt
        ? new Date(right.assignment.dueAt).getTime()
        : Number.POSITIVE_INFINITY)
    );
  });
  return (
    <section className="space-y-4" aria-labelledby="review-work-title">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-[var(--theme-border)] pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-accent)]">
            Hàng đợi cá nhân
          </p>
          <h2 className="mt-1 text-xl font-bold" id="review-work-title">
            Công việc cần xử lý
          </h2>
        </div>
        <p className="text-sm font-semibold text-[var(--theme-muted)]">
          {data.meta.total} hồ sơ trong hàng đợi
        </p>
      </header>
      <p className="text-xs text-[var(--theme-muted)]">
        Việc trễ hạn và đang xử lý được đưa lên trước trong trang này.
      </p>
      <div className="overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)]">
        <div className="divide-y divide-[var(--theme-border)]">
          {orderedAssignments.map((item) => (
            <article
              className="relative grid gap-5 border-l-4 border-l-transparent p-5 transition hover:border-l-[var(--theme-accent)] hover:bg-[var(--theme-elevated)] md:grid-cols-[minmax(0,1fr)_auto] md:items-center lg:p-6"
              key={item.assignment.id}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-xs font-bold",
                      statusClasses[item.assignment.status],
                    )}
                  >
                    {statusLabels[item.assignment.status]}
                  </span>
                  {isOverdue(item.assignment.status, item.assignment.dueAt) ? (
                    <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-bold text-red-800">
                      Trễ hạn
                    </span>
                  ) : null}
                  <span className="font-mono text-xs font-semibold text-[var(--theme-muted)]">
                    {item.dossierCode} · V{item.versionNo}
                  </span>
                </div>
                <h2 className="mt-3 text-lg font-bold tracking-tight">
                  {item.dossierTitle}
                </h2>
                <p className="mt-2 flex items-center gap-2 text-xs font-medium text-[var(--theme-muted)]">
                  <CalendarClock aria-hidden="true" className="size-4" />
                  Hạn xử lý: {formatDate(item.assignment.dueAt)}
                </p>
              </div>
              <Link
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] hover:text-[var(--theme-accent)]"
                href={`/reviews/${item.assignment.id}`}
              >
                <ClipboardCheck aria-hidden="true" className="size-4" />
                {item.assignment.status === "ASSIGNED"
                  ? "Bắt đầu thẩm định"
                  : item.assignment.status === "IN_PROGRESS"
                    ? "Tiếp tục thẩm định"
                    : "Xem phiếu thẩm định"}
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <p className="text-[var(--theme-muted)]">
          Trang {page}/{totalPages}
        </p>
        <div className="flex gap-2">
          {[
            ["Trước", Math.max(1, page - 1), page <= 1],
            ["Sau", Math.min(totalPages, page + 1), page >= totalPages],
          ].map(([label, target, disabled]) => (
            <Link
              aria-disabled={Boolean(disabled)}
              className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 font-semibold text-[var(--theme-text)] aria-disabled:pointer-events-none aria-disabled:opacity-40"
              href={`?${new URLSearchParams({
                ...(status ? { status } : {}),
                page: String(target),
              })}`}
              key={String(label)}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
