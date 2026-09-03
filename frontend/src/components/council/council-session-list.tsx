"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarDays,
  Inbox,
  Landmark,
  LoaderCircle,
  Users,
} from "lucide-react";
import Link from "next/link";

import { councilApi } from "@/lib/api/client";
import type { CouncilListFilters, CouncilSessionStatus } from "@/lib/api/types";
import { councilKeys } from "@/lib/council/query-keys";
import { cn } from "@/lib/utils";

const statusLabels: Record<CouncilSessionStatus, string> = {
  DRAFT: "Chuẩn bị",
  OPEN: "Đang xét duyệt",
  CLOSED: "Đã kết thúc",
};

const statusClasses: Record<CouncilSessionStatus, string> = {
  DRAFT: "border-amber-200 bg-amber-50 text-amber-800",
  OPEN: "border-emerald-200 bg-emerald-50 text-emerald-800",
  CLOSED: "border-neutral-200 bg-neutral-100 text-neutral-700",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function CouncilSessionList({
  page,
  pageSize,
  status,
}: {
  page: number;
  pageSize: number;
  status?: CouncilSessionStatus;
}) {
  const filters: CouncilListFilters = { page, pageSize, status };
  const query = useQuery({
    queryKey: councilKeys.list(filters),
    queryFn: () => councilApi.list(filters),
  });

  if (query.isPending) {
    return (
      <div
        className="grid min-h-64 place-items-center rounded-3xl border bg-white"
        role="status"
      >
        <span className="flex items-center gap-3 text-sm font-semibold text-neutral-600">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang tải các phiên xét duyệt…
        </span>
      </div>
    );
  }
  if (query.error) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800"
        role="alert"
      >
        Chưa thể tải các phiên xét duyệt. Vui lòng thử lại sau.
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div className="rounded-3xl border border-dashed bg-white px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary-50 text-primary-700">
          <Inbox aria-hidden="true" className="size-7" />
        </span>
        <h2 className="mt-5 text-xl font-bold">Chưa có phiên phù hợp</h2>
        <p className="mt-2 text-sm text-neutral-500">
          Các phiên được phân công sẽ xuất hiện tại đây.
        </p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(query.data.meta.total / pageSize));
  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-2">
        {query.data.data.map((item) => (
          <article
            className="group overflow-hidden rounded-2xl border bg-white p-5 transition hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-xl hover:shadow-slate-950/5 sm:p-6"
            key={item.session.id}
          >
            <div className="flex items-start justify-between gap-4">
              <span className="grid size-11 place-items-center rounded-xl bg-ink-950 text-white">
                <Landmark aria-hidden="true" className="size-5" />
              </span>
              <span
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs font-bold",
                  statusClasses[item.session.status],
                )}
              >
                {statusLabels[item.session.status]}
              </span>
            </div>
            <p className="mt-5 font-mono text-xs font-bold text-primary-700">
              {item.session.code}
            </p>
            <h2 className="mt-1 text-xl font-bold tracking-tight">
              {item.session.title}
            </h2>
            <div className="mt-4 grid gap-2 text-sm text-neutral-500 sm:grid-cols-2">
              <p className="flex items-center gap-2">
                <CalendarDays aria-hidden="true" className="size-4" />
                {formatDate(item.session.scheduledAt)}
              </p>
              <p className="flex items-center gap-2">
                <Users aria-hidden="true" className="size-4" />
                {item.session.attendanceCount}/{item.session.memberCount} người
                tham gia · cần tối thiểu {item.session.quorumRequired}
              </p>
            </div>
            <div className="mt-5 flex items-center justify-between gap-3 border-t pt-4">
              <span className="text-xs font-semibold text-neutral-500">
                {item.myAttendanceConfirmedAt
                  ? "Bạn đã xác nhận tham dự"
                  : item.session.status === "DRAFT"
                    ? "Chờ xác nhận tham dự"
                    : "Phiên xét duyệt"}
              </span>
              <Link
                className="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-bold text-primary-700 hover:bg-primary-50"
                href={`/council/${item.session.id}`}
              >
                Mở phiên
                <ArrowRight
                  aria-hidden="true"
                  className="size-4 transition group-hover:translate-x-0.5"
                />
              </Link>
            </div>
          </article>
        ))}
      </div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <p className="text-neutral-500">
          {query.data.meta.total} phiên · Trang {page}/{totalPages}
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
