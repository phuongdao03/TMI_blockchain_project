"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, ExternalLink, FilePenLine, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { adminCertificateApi } from "@/lib/api/client";
import type { CertificateStatus } from "@/lib/api/types";

const statusLabels: Record<CertificateStatus, string> = {
  ACTIVE: "Có hiệu lực",
  EXPIRED: "Hết hiệu lực",
  REVOKED: "Đã thu hồi",
};

export function AdminCertificateManager() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CertificateStatus | "">("");
  const query = useQuery({
    queryKey: ["admin", "certificates", search, status],
    queryFn: () =>
      adminCertificateApi.list({
        search: search.trim() || undefined,
        status: status || undefined,
      }),
  });

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <header>
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          <BadgeCheck className="size-4" /> Quản trị chứng thư
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Chứng thư đã cấp
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
          Chứng thư đã cấp không thể xóa hoặc sửa trực tiếp. Điều chỉnh tạo
          phiên bản mới; trạng thái công khai được quản lý cùng nội dung công
          bố.
        </p>
      </header>

      <div className="grid gap-3 rounded-2xl border bg-white p-4 sm:grid-cols-[1fr_14rem]">
        <label className="relative">
          <span className="sr-only">Tìm chứng thư</span>
          <Search className="absolute left-3 top-3.5 size-4 text-neutral-400" />
          <input
            className="min-h-11 w-full rounded-xl border px-10 text-sm"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Số chứng thư, mã hồ sơ hoặc tên tác phẩm"
            type="search"
            value={search}
          />
        </label>
        <select
          aria-label="Lọc trạng thái chứng thư"
          className="min-h-11 rounded-xl border bg-white px-3 text-sm font-semibold"
          onChange={(event) =>
            setStatus(event.target.value as CertificateStatus | "")
          }
          value={status}
        >
          <option value="">Tất cả trạng thái</option>
          <option value="ACTIVE">Có hiệu lực</option>
          <option value="EXPIRED">Hết hiệu lực</option>
          <option value="REVOKED">Đã thu hồi</option>
        </select>
      </div>

      {query.isPending ? (
        <p role="status">Đang tải danh sách chứng thư…</p>
      ) : null}
      {query.error ? (
        <p className="rounded-xl bg-red-50 p-4 text-sm font-semibold text-red-800">
          Không thể tải danh sách chứng thư.
        </p>
      ) : null}
      {query.data && query.data.data.length === 0 ? (
        <p className="rounded-2xl border border-dashed bg-white p-10 text-center text-neutral-600">
          Không có chứng thư phù hợp bộ lọc.
        </p>
      ) : null}

      <div className="divide-y overflow-hidden rounded-2xl border bg-white">
        {query.data?.data.map((item) => {
          const certificate = item.certificate;
          const visibility =
            certificate.status === "REVOKED"
              ? "Đã thu hồi · chỉ tra cứu"
              : item.isDiscoverable
                ? "Đang công khai"
                : "Chỉ tra cứu trực tiếp";
          return (
            <article
              className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[1fr_auto] lg:items-center"
              key={certificate.id}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
                  <span className="font-mono text-primary-700">
                    {certificate.certificateNumber}
                  </span>
                  <span className="rounded-full bg-neutral-100 px-2.5 py-1">
                    {statusLabels[certificate.status]}
                  </span>
                  <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-900">
                    {visibility}
                  </span>
                </div>
                <h2 className="mt-2 truncate text-lg font-bold">
                  {certificate.assetTitle}
                </h2>
                <p className="mt-1 text-sm text-neutral-500">
                  {certificate.dossierCode} · Phiên bản{" "}
                  {certificate.currentVersionNo}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  className="inline-flex min-h-10 items-center gap-2 rounded-xl border px-3 text-sm font-bold"
                  href={`/verify/${encodeURIComponent(certificate.certificateNumber)}`}
                >
                  Xác minh <ExternalLink className="size-4" />
                </Link>
                {item.publicWorkId ? (
                  <Link
                    className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-neutral-950 px-3 text-sm font-bold text-white"
                    href={`/admin/publications/${item.publicWorkId}`}
                  >
                    Nội dung công bố <FilePenLine className="size-4" />
                  </Link>
                ) : null}
                <Link
                  className="inline-flex min-h-10 items-center rounded-xl border px-3 text-sm font-bold"
                  href={`/certificates/${certificate.id}`}
                >
                  Lịch sử phiên bản
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}
