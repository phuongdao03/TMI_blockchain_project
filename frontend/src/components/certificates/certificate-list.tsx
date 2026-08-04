"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BadgeCheck, LoaderCircle, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { certificateApi } from "@/lib/api/client";

function date(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

export function CertificateList({ page }: { page: number }) {
  const query = useQuery({
    queryKey: ["certificates", page],
    queryFn: () => certificateApi.list(page, 12),
  });
  if (query.isPending) {
    return (
      <div className="grid min-h-64 place-items-center rounded-3xl border bg-white">
        <span className="flex items-center gap-2 text-sm font-semibold text-neutral-600">
          <LoaderCircle className="size-5 animate-spin" /> Đang tải chứng thư…
        </span>
      </div>
    );
  }
  if (query.error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm font-semibold text-red-800">
        Không thể tải danh sách chứng thư. Vui lòng thử lại.
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div className="rounded-3xl border border-dashed bg-white px-6 py-16 text-center">
        <ShieldCheck className="mx-auto size-10 text-primary-700" />
        <h2 className="mt-4 text-xl font-bold">Chưa có chứng thư được phát hành</h2>
        <p className="mt-2 text-sm text-neutral-500">
          Chứng thư sẽ xuất hiện sau khi hồ sơ được thanh toán và neo blockchain.
        </p>
      </div>
    );
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {query.data.data.map((certificate) => (
        <article
          className="group relative overflow-hidden rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-xl"
          key={certificate.id}
        >
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary-700 via-primary-500 to-accent-gold" />
          <div className="flex items-start justify-between gap-4">
            <span className="grid size-11 place-items-center rounded-2xl bg-primary-50 text-primary-700">
              <BadgeCheck className="size-6" />
            </span>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
              {certificate.status}
            </span>
          </div>
          <p className="mt-6 font-mono text-xs font-bold tracking-wider text-primary-700">
            {certificate.certificateNumber}
          </p>
          <h2 className="mt-2 text-xl font-bold tracking-tight">
            {certificate.assetTitle}
          </h2>
          <div className="mt-5 grid grid-cols-2 gap-4 border-t pt-4 text-sm">
            <div>
              <p className="text-xs text-neutral-400">Danh mục</p>
              <p className="mt-1 font-semibold">{certificate.categoryName}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Ngày cấp</p>
              <p className="mt-1 font-semibold">{date(certificate.issuedAt)}</p>
            </div>
          </div>
          <Link
            className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white"
            href={`/chung-thu/${certificate.id}`}
          >
            Xem chứng thư <ArrowUpRight className="size-4" />
          </Link>
        </article>
      ))}
    </div>
  );
}
