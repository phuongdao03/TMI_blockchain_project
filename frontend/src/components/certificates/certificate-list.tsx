"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BadgeCheck,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { certificateApi } from "@/lib/api/client";
import type { CertificateStatus } from "@/lib/api/types";

const certificateStatusLabel: Record<CertificateStatus, string> = {
  ACTIVE: "Có hiệu lực",
  EXPIRED: "Đã hết hiệu lực",
  REVOKED: "Đã thu hồi",
};

export function CertificateList({ page }: { page: number }) {
  const query = useQuery({
    queryKey: ["certificates", page],
    queryFn: () => certificateApi.list(page, 12),
  });
  if (query.isPending) {
    return (
      <div className="grid min-h-64 place-items-center rounded-3xl border bg-white">
        <span className="flex items-center gap-2 text-sm font-semibold text-neutral-600">
          <LoaderCircle className="size-5 animate-spin" /> Đang tải bằng xác
          lập…
        </span>
      </div>
    );
  }
  if (query.error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800">
        Không thể tải danh sách bằng xác lập. Vui lòng thử lại.
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div className="rounded-3xl border border-dashed border-[var(--theme-border)] bg-[var(--theme-surface)] px-6 py-12 text-center text-[var(--theme-text)]">
        <ShieldCheck className="mx-auto size-10 text-primary-700" />
        <h2 className="mt-4 text-xl font-bold">
          Chưa có bằng xác lập được phát hành
        </h2>
        <p className="mt-2 text-sm text-neutral-500">
          Bằng xác lập sẽ xuất hiện sau khi hồ sơ hoàn tất lệ phí và được phát
          hành.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary-700 px-5 text-sm font-bold text-white"
          href="/dossiers"
        >
          Theo dõi hồ sơ của tôi
        </Link>
      </div>
    );
  }
  const ordered = [...query.data.data].sort(
    (left, right) =>
      Number(right.status === "ACTIVE") - Number(left.status === "ACTIVE"),
  );
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {ordered.map((certificate) => (
        <article
          className="group relative overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 text-[var(--theme-text)] shadow-sm transition hover:shadow-lg sm:p-6"
          key={certificate.id}
        >
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary-700 via-primary-500 to-accent-gold" />
          <div className="flex items-start justify-between gap-4">
            <span className="grid size-11 place-items-center rounded-2xl bg-primary-50 text-primary-700">
              <BadgeCheck className="size-6" />
            </span>
            <span
              className={`rounded-full px-3 py-1 text-xs font-bold ${certificate.status === "ACTIVE" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}
            >
              {certificateStatusLabel[certificate.status]}
            </span>
          </div>
          <p className="mt-6 font-mono text-xs font-bold tracking-wider text-primary-700">
            {certificate.certificateNumber}
          </p>
          <h2 className="mt-2 text-xl font-bold tracking-tight">
            {certificate.assetTitle}
          </h2>
          {certificate.status === "REVOKED" ? (
            <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
              Mã cũ được giữ để đối chiếu lịch sử. Hãy dùng bằng THV mới nếu đã
              được tái cấp.
            </p>
          ) : null}
          <div className="mt-5 grid grid-cols-2 gap-4 border-t pt-4 text-sm">
            <div>
              <p className="text-xs text-neutral-400">Danh mục</p>
              <p className="mt-1 font-semibold">{certificate.categoryName}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Phiên bản</p>
              <p className="mt-1 font-semibold">
                {certificate.currentVersionNo}
              </p>
            </div>
          </div>
          <Link
            className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary-700 px-4 text-sm font-bold text-white sm:w-auto"
            href={`/certificates/${certificate.id}`}
          >
            {certificate.status === "ACTIVE"
              ? "Xem và tải bằng"
              : "Xem lịch sử"}{" "}
            <ArrowUpRight className="size-4" />
          </Link>
        </article>
      ))}
    </div>
  );
}
