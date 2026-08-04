"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Blocks, Clock3, Gauge, ReceiptText } from "lucide-react";

import { operationsApi } from "@/lib/api/client";

export function OperationsDashboard() {
  const metrics = useQuery({ queryKey: ["admin", "operations"], queryFn: operationsApi.metrics });
  if (metrics.isPending) return <p role="status">Đang tổng hợp dữ liệu vận hành...</p>;
  if (!metrics.data) return <p className="text-error" role="alert">Không thể tải dashboard vận hành.</p>;
  const cards = [
    ["SLA quá hạn", metrics.data.overdueReviews, Clock3],
    ["Thanh toán lỗi", metrics.data.paymentFailures, ReceiptText],
    ["Blockchain lỗi", metrics.data.blockchainFailures, Blocks],
    [
      "Cache public hit",
      metrics.data.publicCatalogCacheHitRatio.toLocaleString("vi-VN", {
        style: "percent",
        maximumFractionDigits: 1,
      }),
      Gauge,
    ],
  ] as const;
  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header><p className="flex items-center gap-2 text-sm font-bold text-primary-700"><AlertTriangle className="size-4" />Kiểm soát vận hành</p><h1 className="mt-2 text-3xl font-bold">Dashboard vận hành</h1><p className="mt-2 text-sm text-neutral-600">Theo dõi funnel hồ sơ, SLA và các hàng đợi cần can thiệp.</p></header>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, Icon]) => <article className="rounded-2xl border border-neutral-200 bg-white p-5" key={label}><Icon className="size-5 text-primary-700" /><p className="mt-5 text-3xl font-bold">{value}</p><p className="mt-1 text-sm text-neutral-600">{label}</p></article>)}</section>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-neutral-200 bg-white p-5"><h2 className="font-bold">Funnel hồ sơ</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{Object.entries(metrics.data.dossierFunnel).map(([status, count]) => <div className="flex items-center justify-between rounded-xl bg-neutral-50 px-4 py-3" key={status}><span className="text-sm font-semibold">{status}</span><strong>{count}</strong></div>)}</div></section>
        <section className="rounded-2xl border border-neutral-200 bg-white p-5"><h2 className="font-bold">Tải thẩm định</h2><div className="mt-4 space-y-3">{metrics.data.reviewerWorkload.length === 0 ? <p className="text-sm text-neutral-500">Không có phân công đang hoạt động.</p> : metrics.data.reviewerWorkload.map((row) => <div className="flex items-center justify-between" key={row.userId}><span className="truncate font-mono text-xs text-neutral-600">{row.userId}</span><strong>{row.activeAssignments}</strong></div>)}</div></section>
      </div>
    </div>
  );
}
