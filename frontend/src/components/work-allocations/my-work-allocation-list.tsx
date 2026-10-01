"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardList, Inbox, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { reviewApi, workAllocationSelfApi } from "@/lib/api/client";

const statusLabels = {
  DRAFT: "Chờ kích hoạt",
  ACTIVE: "Đang thực hiện",
  COMPLETED: "Hoàn thành",
  CANCELLED: "Đã hủy",
} as const;

const priorityLabels = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Khẩn cấp",
} as const;

const reviewStates = {
  ASSIGNED: {
    label: "Mới được giao",
    tone: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200",
    action: "Bắt đầu thẩm định",
  },
  IN_PROGRESS: {
    label: "Đang thực hiện",
    tone: "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-700 dark:bg-sky-950/40 dark:text-sky-200",
    action: "Tiếp tục thẩm định",
  },
  SUBMITTED: {
    label: "Đã gửi kết quả",
    tone: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200",
    action: "Xem kết quả",
  },
  CONFLICTED: {
    label: "Đã kết thúc",
    tone: "border-neutral-300 bg-neutral-100 text-neutral-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200",
    action: "Xem hồ sơ",
  },
  CANCELLED: {
    label: "Đã hủy",
    tone: "border-neutral-300 bg-neutral-100 text-neutral-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200",
    action: "Xem hồ sơ",
  },
} as const;

type ReviewFilter = "ALL" | "OPEN" | "DONE";

export function MyWorkAllocationList() {
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("OPEN");
  const allocations = useQuery({
    queryKey: ["my-work-allocations"],
    queryFn: () => workAllocationSelfApi.list({ pageSize: 50 }),
  });
  const reviews = useQuery({
    queryKey: ["my-review-assignments", "work-allocations"],
    queryFn: () => reviewApi.list({ pageSize: 100 }),
  });
  const separateReviews = reviews.data?.data ?? [];
  const otherAllocations = (allocations.data?.data ?? []).filter(
    (allocation) =>
      allocation.kind !== "DOSSIER_REVIEW" ||
      !separateReviews.some(
        (review) =>
          review.assignment.dossierId === allocation.dossierId &&
          review.assignment.dossierVersionId === allocation.dossierVersionId,
      ),
  );
  const openReviews = separateReviews.filter(
    (item) =>
      item.assignment.status === "ASSIGNED" ||
      item.assignment.status === "IN_PROGRESS",
  );
  const visibleReviews = separateReviews.filter(
    (item) =>
      reviewFilter === "ALL" ||
      (reviewFilter === "OPEN"
        ? item.assignment.status === "ASSIGNED" ||
          item.assignment.status === "IN_PROGRESS"
        : item.assignment.status !== "ASSIGNED" &&
          item.assignment.status !== "IN_PROGRESS"),
  );

  return (
    <section
      aria-labelledby="my-work-allocations-title"
      className="mx-auto max-w-5xl space-y-6 pb-12"
    >
      <header className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 py-6 text-[var(--theme-text)] sm:px-8 sm:py-7">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--theme-accent)]">
          <ClipboardList aria-hidden="true" className="size-4" />
          Trung tâm công việc
        </div>
        <h1
          className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
          id="my-work-allocations-title"
        >
          Công việc được giao
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
          Theo dõi đầu việc chung và các hồ sơ thẩm định mà bạn đang tham gia.
        </p>
      </header>
      {allocations.isPending || reviews.isPending ? <LoadingState /> : null}
      {allocations.isError ? <ErrorState /> : null}
      {reviews.isError ? (
        <p
          role="alert"
          className="rounded-xl border border-red-200 p-4 text-sm text-red-800"
        >
          Chưa tải được hồ sơ thẩm định. Mở hàng đợi để kiểm tra trực tiếp.
        </p>
      ) : null}
      {allocations.data &&
      reviews.data &&
      allocations.data.data.length === 0 &&
      reviews.data.data.length === 0 ? (
        <EmptyState />
      ) : null}
      {separateReviews.length > 0 ? (
        <section aria-label="Hồ sơ thẩm định được giao" className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-[var(--theme-text)]">
                Hồ sơ thẩm định
              </h2>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                {openReviews.length} cần xử lý ·{" "}
                {separateReviews.length - openReviews.length} đã kết thúc
              </p>
            </div>
            <div
              aria-label="Lọc hồ sơ thẩm định"
              className="inline-flex gap-1 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-1"
            >
              {(
                [
                  ["OPEN", "Cần xử lý"],
                  ["DONE", "Đã kết thúc"],
                  ["ALL", "Tất cả"],
                ] as const
              ).map(([value, label]) => (
                <button
                  aria-pressed={reviewFilter === value}
                  className={`min-h-10 rounded-lg px-3 text-sm font-semibold transition ${reviewFilter === value ? "bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]" : "text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)]"}`}
                  key={value}
                  onClick={() => setReviewFilter(value)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {(reviews.data?.meta.total ?? 0) > separateReviews.length ? (
            <p className="text-sm text-[var(--theme-muted)]">
              Đang hiển thị {separateReviews.length}/{reviews.data?.meta.total}{" "}
              hồ sơ gần nhất.{" "}
              <Link
                className="font-semibold text-[var(--theme-accent)] underline"
                href="/reviews"
              >
                Xem toàn bộ hàng đợi
              </Link>
            </p>
          ) : null}
          {visibleReviews.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
              Không có hồ sơ trong nhóm này.
            </p>
          ) : null}
          {visibleReviews.map((item) => (
            <article
              className="grid gap-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
              key={item.assignment.id}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-md border px-2.5 py-1 text-xs font-bold ${reviewStates[item.assignment.status].tone}`}
                  >
                    {reviewStates[item.assignment.status].label}
                  </span>
                  <span className="font-mono text-xs text-[var(--theme-muted)]">
                    {item.dossierCode} · Phiên bản {item.versionNo}
                  </span>
                </div>
                <h3 className="mt-2 text-base font-bold text-[var(--theme-text)]">
                  {item.dossierTitle}
                </h3>
                <p className="mt-1 text-xs text-[var(--theme-muted)]">
                  {item.assignment.dueAt
                    ? `Hạn ${new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(item.assignment.dueAt))}`
                    : "Chưa đặt hạn xử lý"}
                </p>
              </div>
              <Link
                aria-label={`${reviewStates[item.assignment.status].action}: ${item.dossierTitle}`}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)]"
                href={`/reviews/${item.assignment.id}`}
              >
                {reviewStates[item.assignment.status].action}{" "}
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </section>
      ) : null}
      {otherAllocations.length ? (
        <section aria-label="Đầu việc khác" className="space-y-3">
          <h2 className="text-xl font-bold text-[var(--theme-text)]">
            Đầu việc khác
          </h2>
          <div className="grid gap-3" role="list">
            {otherAllocations.map((allocation) => (
              <article
                className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-[var(--theme-text)] sm:p-5"
                key={allocation.id}
                role="listitem"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--theme-accent)]">
                      {allocation.kind === "DOSSIER_REVIEW"
                        ? "Hồ sơ thẩm định"
                        : "Công việc chung"}
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-[var(--theme-text)]">
                      {allocation.objective}
                    </h2>
                  </div>
                  <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
                    {statusLabels[allocation.status]}
                  </span>
                </div>
                <p className="mt-3 text-sm text-[var(--theme-muted)]">
                  Ưu tiên {priorityLabels[allocation.priority]}
                  {allocation.dueAt
                    ? ` · Hạn ${new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(allocation.dueAt))}`
                    : " · Chưa đặt hạn"}
                </p>
                {allocation.kind === "DOSSIER_REVIEW" ? (
                  <Link
                    className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 transition hover:border-primary-400 hover:text-primary-700 dark:border-neutral-700 dark:text-neutral-100 dark:hover:border-primary-400 dark:hover:text-primary-200"
                    href="/reviews"
                  >
                    Mở hàng đợi thẩm định{" "}
                    <ArrowRight aria-hidden="true" className="size-4" />
                  </Link>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

function LoadingState() {
  return (
    <div
      aria-busy="true"
      className="grid min-h-56 place-items-center"
      role="status"
    >
      <LoaderCircle
        aria-hidden="true"
        className="size-6 animate-spin text-[var(--theme-accent)]"
      />
      <span className="sr-only">Đang tải công việc được giao</span>
    </div>
  );
}

function ErrorState() {
  return (
    <p
      className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm font-semibold text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
      role="alert"
    >
      Chưa thể tải công việc được giao. Vui lòng thử lại.
    </p>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-neutral-300 px-5 py-10 text-center dark:border-neutral-700">
      <Inbox aria-hidden="true" className="mx-auto size-9 text-neutral-400" />
      <h2 className="mt-4 text-xl font-bold text-neutral-950 dark:text-white">
        Chưa có công việc được giao
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600 dark:text-neutral-300">
        Khi được phân công, đầu việc hoặc hồ sơ cần thẩm định sẽ xuất hiện tại
        đây.
      </p>
      <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">
        Tài khoản kiểm duyệt đã sẵn sàng. Quản trị viên cần giao việc hoặc phân
        công hồ sơ để bạn bắt đầu.
      </p>
    </div>
  );
}
