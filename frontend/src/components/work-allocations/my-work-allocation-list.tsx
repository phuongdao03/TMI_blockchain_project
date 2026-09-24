"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardList, Inbox, LoaderCircle } from "lucide-react";
import Link from "next/link";

import { workAllocationSelfApi } from "@/lib/api/client";

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

export function MyWorkAllocationList() {
  const allocations = useQuery({
    queryKey: ["my-work-allocations"],
    queryFn: () => workAllocationSelfApi.list({ pageSize: 50 }),
  });

  return (
    <section
      aria-labelledby="my-work-allocations-title"
      className="mx-auto max-w-5xl space-y-6 pb-12"
    >
      <header className="rounded-2xl border border-neutral-800 bg-neutral-950 px-5 py-6 text-white sm:px-8 sm:py-7">
        <div className="flex items-center gap-3 text-sm font-semibold text-primary-200">
          <ClipboardList aria-hidden="true" className="size-4" />
          Trung tâm công việc
        </div>
        <h1
          className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
          id="my-work-allocations-title"
        >
          Công việc được giao
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
          Theo dõi đầu việc chung và các hồ sơ thẩm định mà bạn đang tham gia.
        </p>
      </header>
      {allocations.isPending ? <LoadingState /> : null}
      {allocations.isError ? <ErrorState /> : null}
      {allocations.data && allocations.data.data.length === 0 ? (
        <EmptyState />
      ) : null}
      {allocations.data?.data.length ? (
        <div className="grid gap-3" role="list">
          {allocations.data.data.map((allocation) => (
            <article
              className="rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900 sm:p-5"
              key={allocation.id}
              role="listitem"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-primary-700 dark:text-primary-300">
                    {allocation.kind === "DOSSIER_REVIEW"
                      ? "Hồ sơ thẩm định"
                      : "Công việc chung"}
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-neutral-950 dark:text-white">
                    {allocation.objective}
                  </h2>
                </div>
                <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
                  {statusLabels[allocation.status]}
                </span>
              </div>
              <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">
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
        className="size-6 animate-spin text-primary-700"
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
    </div>
  );
}
