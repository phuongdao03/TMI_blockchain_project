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
  ASSIGNED: "Chờ xác nhận",
  IN_PROGRESS: "Đang thẩm định",
  CONFLICTED: "Đã báo xung đột",
  SUBMITTED: "Đã gửi kết quả",
  CANCELLED: "Đã hủy",
};

const statusClasses: Record<ReviewAssignmentStatus, string> = {
  ASSIGNED: "border-amber-200 bg-amber-50 text-amber-800",
  IN_PROGRESS: "border-blue-200 bg-blue-50 text-blue-800",
  CONFLICTED: "border-red-200 bg-red-50 text-red-800",
  SUBMITTED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  CANCELLED: "border-neutral-200 bg-neutral-100 text-neutral-600",
};

function formatDate(value: string | null) {
  if (!value) return "Không giới hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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
  const { data, error, isPending } = useQuery({
    queryKey: reviewKeys.list(filters),
    queryFn: () => reviewApi.list(filters),
  });

  if (isPending) {
    return (
      <div
        className="grid min-h-64 place-items-center rounded-2xl border bg-white"
        role="status"
      >
        <span className="flex items-center gap-3 text-sm font-semibold text-neutral-600">
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
        Không thể tải hàng đợi thẩm định. Vui lòng thử lại.
      </div>
    );
  }
  if (!data?.data.length) {
    return (
      <div className="rounded-3xl border border-dashed bg-white px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary-50 text-primary-700">
          <Inbox aria-hidden="true" className="size-7" />
        </span>
        <h2 className="mt-5 text-xl font-bold">Không có hồ sơ phù hợp</h2>
        <p className="mt-2 text-sm text-neutral-500">
          Hàng đợi sẽ cập nhật khi bạn được phân công hồ sơ mới.
        </p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.meta.total / pageSize));
  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border bg-white">
        <div className="divide-y divide-neutral-100">
          {data.data.map((item) => (
            <article
              className="grid gap-5 p-5 transition hover:bg-neutral-50/80 md:grid-cols-[minmax(0,1fr)_auto] md:items-center lg:p-6"
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
                  <span className="font-mono text-xs font-semibold text-neutral-500">
                    {item.dossierCode} · V{item.versionNo}
                  </span>
                </div>
                <h2 className="mt-3 text-lg font-bold tracking-tight">
                  {item.dossierTitle}
                </h2>
                <p className="mt-2 flex items-center gap-2 text-xs font-medium text-neutral-500">
                  <CalendarClock aria-hidden="true" className="size-4" />
                  Hạn xử lý: {formatDate(item.assignment.dueAt)}
                </p>
              </div>
              <Link
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border bg-white px-4 text-sm font-bold text-neutral-800 hover:border-primary-200 hover:text-primary-700"
                href={`/reviews/${item.assignment.id}`}
              >
                <ClipboardCheck aria-hidden="true" className="size-4" />
                Mở hồ sơ thẩm định
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <p className="text-neutral-500">
          {data.meta.total} phân công · Trang {page}/{totalPages}
        </p>
        <div className="flex gap-2">
          {[
            ["Trước", Math.max(1, page - 1), page <= 1],
            ["Sau", Math.min(totalPages, page + 1), page >= totalPages],
          ].map(([label, target, disabled]) => (
            <Link
              aria-disabled={Boolean(disabled)}
              className="inline-flex min-h-11 items-center rounded-xl border bg-white px-4 font-semibold aria-disabled:pointer-events-none aria-disabled:opacity-40"
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
    </div>
  );
}
