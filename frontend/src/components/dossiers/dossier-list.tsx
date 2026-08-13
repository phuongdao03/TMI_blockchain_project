"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FilePlus2,
  FolderSearch,
  LoaderCircle,
} from "lucide-react";
import Link from "next/link";

import { DossierStatusBadge } from "@/components/dossiers/dossier-status";
import { dossierApi } from "@/lib/api/client";
import type { DossierListFilters, DossierStatus } from "@/lib/api/types";
import { dossierKeys } from "@/lib/dossiers/query-keys";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export function DossierList({
  page,
  pageSize,
  status,
}: {
  page: number;
  pageSize: number;
  status?: DossierStatus;
}) {
  const filters: DossierListFilters = { page, pageSize, status };
  const { data, error, isPending } = useQuery({
    queryKey: dossierKeys.list(filters),
    queryFn: () => dossierApi.list(filters),
  });

  if (isPending) {
    return (
      <div
        className="grid min-h-64 place-items-center rounded-2xl border border-neutral-200 bg-white"
        role="status"
      >
        <span className="flex items-center gap-3 text-sm font-semibold text-neutral-600">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang tải hồ sơ…
        </span>
      </div>
    );
  }
  if (error) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-medium text-red-800"
        role="alert"
      >
        Không thể tải danh sách hồ sơ. Vui lòng thử lại.
      </div>
    );
  }
  if (!data?.data.length) {
    return (
      <div className="relative overflow-hidden rounded-3xl border border-dashed border-neutral-300 bg-white px-6 py-16 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary-50 text-primary-700">
          <FolderSearch aria-hidden="true" className="size-7" />
        </span>
        <h2 className="mt-5 text-xl font-bold">Chưa có hồ sơ phù hợp</h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-500">
          Tạo hồ sơ đầu tiên để chuẩn bị dữ liệu và bằng chứng xác lập.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-700"
          href="/dossiers/new"
        >
          <FilePlus2 aria-hidden="true" className="size-4" />
          Tạo hồ sơ
        </Link>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.meta.total / pageSize));
  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="divide-y divide-neutral-100">
          {data.data.map((dossier) => (
            <article
              className="group grid gap-5 p-5 transition-colors hover:bg-neutral-50/80 md:grid-cols-[minmax(0,1fr)_auto] md:items-center lg:p-6"
              key={dossier.id}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <DossierStatusBadge status={dossier.status} />
                  <span className="font-mono text-xs font-semibold tracking-wide text-neutral-500">
                    {dossier.code}
                  </span>
                </div>
                <h2 className="mt-3 truncate text-lg font-bold tracking-tight text-neutral-950">
                  {dossier.title}
                </h2>
                <p className="mt-1 line-clamp-2 text-sm leading-6 text-neutral-500">
                  {dossier.summary ?? "Chưa có mô tả hồ sơ."}
                </p>
                <p className="mt-3 text-xs font-medium text-neutral-400">
                  Cập nhật {formatDate(dossier.updatedAt)}
                  {dossier.currentVersionNo > 0
                    ? ` · Phiên bản ${dossier.currentVersionNo}`
                    : ""}
                </p>
              </div>
              <Link
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 text-sm font-bold text-neutral-800 transition group-hover:border-primary-200 group-hover:text-primary-700"
                href={`/dossiers/${dossier.id}`}
              >
                {dossier.canEdit ? "Tiếp tục hoàn thiện" : "Xem hồ sơ"}
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <p className="text-neutral-500">
          {data.meta.total} hồ sơ · Trang {page}/{totalPages}
        </p>
        <div className="flex gap-2">
          <Link
            aria-disabled={page <= 1}
            className="inline-flex min-h-11 items-center rounded-xl border border-neutral-200 bg-white px-4 font-semibold aria-disabled:pointer-events-none aria-disabled:opacity-40"
            href={`?${new URLSearchParams({
              ...(status ? { status } : {}),
              page: String(Math.max(1, page - 1)),
            })}`}
          >
            Trước
          </Link>
          <Link
            aria-disabled={page >= totalPages}
            className="inline-flex min-h-11 items-center rounded-xl border border-neutral-200 bg-white px-4 font-semibold aria-disabled:pointer-events-none aria-disabled:opacity-40"
            href={`?${new URLSearchParams({
              ...(status ? { status } : {}),
              page: String(Math.min(totalPages, page + 1)),
            })}`}
          >
            Sau
          </Link>
        </div>
      </div>
    </div>
  );
}
