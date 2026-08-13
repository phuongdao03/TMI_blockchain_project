"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowDown,
  BadgeCheck,
  Clock3,
  Files,
  ReceiptText,
} from "lucide-react";

import { operationsApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { JobOperationsWorkspace } from "@/components/admin/job-operations-workspace";

const dossierStatusLabels: Record<string, string> = {
  DRAFT: "Đang hoàn thiện",
  SUBMITTED: "Chờ kiểm tra",
  PRECHECK: "Đang kiểm tra",
  UNDER_REVIEW: "Đang thẩm định",
  REVISION_REQUESTED: "Chờ bổ sung",
  COUNCIL_REVIEW: "Chờ xét duyệt",
  PAYMENT_PENDING: "Chờ thanh toán",
  APPROVED: "Đã phê duyệt",
  REJECTED: "Không được phê duyệt",
  CERTIFICATE_ISSUED: "Đã phát hành chứng thư",
};

export function OperationsDashboard({
  showHeader = true,
}: {
  showHeader?: boolean;
}) {
  const user = useAuthUser();
  const metrics = useQuery({
    queryKey: ["admin", "operations"],
    queryFn: operationsApi.metrics,
  });
  if (metrics.isPending)
    return <p role="status">Đang tổng hợp dữ liệu vận hành...</p>;
  if (!metrics.data)
    return (
      <p className="text-error" role="alert">
        Không thể tải tổng quan vận hành. Vui lòng thử lại.
      </p>
    );
  const activeDossiers = Object.entries(metrics.data.dossierFunnel)
    .filter(([status]) => !["REJECTED", "CERTIFICATE_ISSUED"].includes(status))
    .reduce((total, [, count]) => total + count, 0);
  const cards = [
    ["Hồ sơ trễ hạn", metrics.data.overdueReviews, Clock3],
    ["Thanh toán cần kiểm tra", metrics.data.paymentFailures, ReceiptText],
    ["Phát hành cần xử lý", metrics.data.blockchainFailures, BadgeCheck],
    ["Hồ sơ đang xử lý", activeDossiers, Files],
  ] as const;
  const urgentCount =
    metrics.data.overdueReviews +
    metrics.data.paymentFailures +
    metrics.data.blockchainFailures;
  const maxStageCount = Math.max(
    1,
    ...Object.values(metrics.data.dossierFunnel),
  );
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {showHeader ? (
        <header>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
            Trung tâm điều hành
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
            Tổng quan vận hành
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
            Ưu tiên hồ sơ trễ hạn, thanh toán chưa hoàn tất và sự cố phát hành.
          </p>
        </header>
      ) : null}

      <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-[#151515] px-6 py-8 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
        <div className="relative z-10">
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-gold-300">
            Ưu tiên hôm nay
          </p>
          <p className="mt-4 text-5xl font-bold tracking-[-0.05em] sm:text-6xl">
            {urgentCount}
          </p>
          <h2 className="mt-2 text-xl font-bold">việc cần được xử lý sớm</h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
            Bắt đầu với hồ sơ quá hạn, sau đó kiểm tra thanh toán và các trường
            hợp phát hành chưa hoàn tất.
          </p>
        </div>
        <a
          className="relative z-10 mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-500 lg:mt-0"
          href="#hang-doi-xu-ly"
        >
          Xem việc cần xử lý
          <ArrowDown aria-hidden="true" className="size-4" />
        </a>
      </section>

      <section
        className="grid overflow-hidden rounded-xl border border-black/10 bg-[#fbfaf7] md:grid-cols-2 xl:grid-cols-4"
        aria-label="Chỉ số cần theo dõi"
      >
        {cards.map(([label, value, Icon]) => (
          <article
            className="border-b border-black/8 p-6 last:border-b-0 md:border-r md:[&:nth-child(2)]:border-r-0 xl:border-b-0 xl:[&:nth-child(2)]:border-r xl:last:border-r-0"
            key={label}
          >
            <div className="flex items-start justify-between gap-4">
              <p className="text-4xl font-bold tracking-[-0.04em]">{value}</p>
              <Icon className="size-5 text-primary-700" />
            </div>
            <p className="mt-4 text-sm font-semibold text-neutral-600">
              {label}
            </p>
          </article>
        ))}
      </section>

      <div
        className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]"
        id="hang-doi-xu-ly"
      >
        <section className="rounded-xl border border-black/10 bg-[#fbfaf7] p-6">
          <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
            Tiến độ hồ sơ
          </p>
          <h2 className="mt-2 text-xl font-bold">Hồ sơ theo giai đoạn</h2>
          <div className="mt-6 space-y-5">
            {Object.entries(metrics.data.dossierFunnel).map(
              ([status, count]) => (
                <div key={status}>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-semibold">
                      {dossierStatusLabels[status] ?? "Đang xử lý"}
                    </span>
                    <strong className="font-mono text-sm">{count}</strong>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-200">
                    <div
                      aria-hidden="true"
                      className="h-full rounded-full bg-primary-600"
                      style={{
                        width: `${Math.max(7, (count / maxStageCount) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ),
            )}
          </div>
        </section>
        <section className="rounded-xl border border-black/10 bg-[#1d1c1b] p-6 text-white">
          <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-gold-300">
            Phân công hiện tại
          </p>
          <h2 className="mt-2 text-xl font-bold">Khối lượng thẩm định</h2>
          <div className="mt-6 divide-y divide-white/10">
            {metrics.data.reviewerWorkload.length === 0 ? (
              <p className="py-5 text-sm text-slate-400">
                Không có phân công đang hoạt động.
              </p>
            ) : (
              metrics.data.reviewerWorkload.map((row) => (
                <div
                  className="flex items-center justify-between gap-4 py-4"
                  key={row.reviewerEmail}
                >
                  <span className="truncate text-sm font-medium text-slate-300">
                    {row.reviewerEmail}
                  </span>
                  <strong className="grid size-9 place-items-center rounded-full border border-white/10 bg-white/5">
                    {row.activeAssignments}
                  </strong>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
      {user?.roles.includes("SUPER_ADMIN") ? <JobOperationsWorkspace /> : null}
    </div>
  );
}
