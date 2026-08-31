"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowDown,
  BadgeCheck,
  Clock3,
  Files,
  ReceiptText,
  RefreshCw,
} from "lucide-react";

import {
  OperationsRiskChart,
  ReviewerWorkloadChart,
} from "@/components/admin/operations-charts";
import { JobOperationsWorkspace } from "@/components/admin/job-operations-workspace";
import { operationsApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";

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

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3">
        <p className="text-xs font-medium text-neutral-500">
          Dữ liệu hiện tại · cập nhật lúc{" "}
          {new Date(metrics.dataUpdatedAt).toLocaleTimeString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
        <button
          aria-label="Làm mới dữ liệu"
          className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-xs font-bold hover:bg-[var(--theme-elevated)] disabled:opacity-60"
          disabled={metrics.isFetching}
          onClick={() => void metrics.refetch()}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={`size-4 ${metrics.isFetching ? "animate-spin" : ""}`}
          />
          {metrics.isFetching ? "Đang cập nhật" : "Làm mới"}
        </button>
      </div>

      <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-[#151515] px-5 py-7 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
        <div className="relative z-10">
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-gold-300">
            Ưu tiên hôm nay
          </p>
          <p className="mt-4 text-4xl font-bold tracking-[-0.05em] sm:text-6xl">
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
        className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4"
        aria-label="Chỉ số cần theo dõi"
      >
        {cards.map(([label, value, Icon]) => (
          <article
            className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
            key={label}
          >
            <div className="flex items-start justify-between gap-2 sm:gap-4">
              <p className="text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
                {value}
              </p>
              <Icon className="size-5 text-primary-700" />
            </div>
            <p className="mt-3 text-xs font-semibold leading-5 text-neutral-600 sm:mt-4 sm:text-sm">
              {label}
            </p>
          </article>
        ))}
      </section>

      <div
        className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]"
        id="hang-doi-xu-ly"
      >
        <section className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
          <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
            Tiến độ hồ sơ
          </p>
          <h2 className="mt-2 text-xl font-bold">Hồ sơ theo giai đoạn</h2>
          <div
            aria-label="Biểu đồ số hồ sơ theo giai đoạn"
            className="mt-6 space-y-5"
            role="img"
          >
            {Object.entries(metrics.data.dossierFunnel).map(
              ([status, count]) => (
                <div key={status}>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-semibold">
                      {dossierStatusLabels[status] ?? "Đang xử lý"}
                    </span>
                    <strong className="font-mono text-sm">{count}</strong>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--theme-elevated)]">
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
        <section className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
          <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
            Phân bổ rủi ro
          </p>
          <h2 className="mt-2 text-xl font-bold">Cơ cấu cảnh báo</h2>
          <div className="mt-6">
            <OperationsRiskChart
              blockchainFailures={metrics.data.blockchainFailures}
              overdueReviews={metrics.data.overdueReviews}
              paymentFailures={metrics.data.paymentFailures}
            />
          </div>
        </section>
      </div>
      <section className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
              Phân công hiện tại
            </p>
            <h2 className="mt-2 text-xl font-bold">Khối lượng thẩm định</h2>
          </div>
          <p className="text-xs text-neutral-500">Số hồ sơ đang hoạt động</p>
        </div>
        <div className="mt-6">
          <ReviewerWorkloadChart rows={metrics.data.reviewerWorkload} />
        </div>
      </section>
      {user?.roles.includes("SUPER_ADMIN") ? <JobOperationsWorkspace /> : null}
    </div>
  );
}
