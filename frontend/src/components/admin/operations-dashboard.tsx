"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowUpRight,
  BadgeCheck,
  Clock3,
  Files,
  ReceiptText,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";

import {
  OperationsJobHealthChart,
  OperationsRiskChart,
  ReviewerWorkloadChart,
} from "@/components/admin/operations-charts";
import { JobOperationsWorkspace } from "@/components/admin/job-operations-workspace";
import { adminReviewApi, ApiError, operationsApi } from "@/lib/api/client";
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
  CERTIFICATE_ISSUED: "Đã phát hành bằng xác lập",
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
  const reviewQueue = useQuery({
    queryKey: ["admin", "operations", "review-queue-fallback"],
    queryFn: () => adminReviewApi.list({ pageSize: 1 }),
    enabled: metrics.isError,
  });
  if (metrics.isPending)
    return (
      <section
        aria-label="Đang tải tổng quan vận hành"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        role="status"
      >
        <span className="sr-only">Đang tổng hợp dữ liệu vận hành...</span>
        {Array.from({ length: 4 }, (_, index) => (
          <span
            aria-hidden="true"
            className="h-28 animate-pulse rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
            key={index}
          />
        ))}
      </section>
    );
  if (!metrics.data) {
    const error = metrics.error instanceof ApiError ? metrics.error : null;
    return (
      <section
        className="rounded-xl border border-error/30 bg-[var(--theme-surface)] p-5"
        role="alert"
      >
        <h2 className="font-bold text-[var(--theme-text)]">
          Chưa tải được tổng quan vận hành
        </h2>
        <p className="mt-2 text-sm text-[var(--theme-muted)]">
          {error?.status === 403
            ? "Tài khoản này chưa có quyền xem chỉ số vận hành."
            : error?.status === 401
              ? "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại."
              : "Không thể kết nối với dịch vụ vận hành. Bạn vẫn có thể xử lý hồ sơ."}
        </p>
        {error ? (
          <p className="mt-2 text-xs text-[var(--theme-muted)]">
            Mã lỗi: {error.code}
            {error.requestId ? ` · Mã yêu cầu: ${error.requestId}` : ""}
          </p>
        ) : null}
        {reviewQueue.data ? (
          <p className="mt-3 text-sm font-semibold text-[var(--theme-text)]">
            {reviewQueue.data.meta.total} hồ sơ đang chờ kiểm tra hoặc thẩm
            định.
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white disabled:opacity-60"
            disabled={metrics.isFetching}
            onClick={() => void metrics.refetch()}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={`size-4 ${metrics.isFetching ? "animate-spin" : ""}`}
            />
            {metrics.isFetching ? "Đang tải lại" : "Thử tải lại tổng quan"}
          </button>
          <Link
            className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)]"
            href="/admin/reviews"
          >
            Xem hồ sơ chờ xử lý
          </Link>
        </div>
      </section>
    );
  }
  const activeDossiers = Object.entries(metrics.data.dossierFunnel)
    .filter(([status]) => !["REJECTED", "CERTIFICATE_ISSUED"].includes(status))
    .reduce((total, [, count]) => total + count, 0);
  const cards = [
    ["Hồ sơ trễ hạn", metrics.data.overdueReviews, Clock3, "/admin/reviews"],
    [
      "Thanh toán cần kiểm tra",
      metrics.data.paymentFailures,
      ReceiptText,
      "/admin/payments",
    ],
    [
      "Phát hành cần xử lý",
      metrics.data.blockchainFailures,
      BadgeCheck,
      "/admin/certificates",
    ],
    ["Hồ sơ đang xử lý", activeDossiers, Files, "/admin/reviews"],
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
    <div className="mx-auto max-w-7xl space-y-8 text-[var(--theme-text)]">
      {showHeader ? (
        <header>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
            Trung tâm điều hành
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
            Tổng quan vận hành
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
            Ưu tiên hồ sơ trễ hạn, thanh toán chưa hoàn tất và sự cố phát hành.
          </p>
        </header>
      ) : null}

      {!showHeader ? (
        <section
          aria-label="Số hồ sơ theo bước xử lý"
          className="divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)] sm:grid sm:grid-cols-3 sm:gap-3 sm:divide-y-0 sm:border-0"
        >
          {(
            [
              ["SUBMITTED", "Đã nộp"],
              ["PRECHECK", "Đang kiểm tra"],
              ["UNDER_REVIEW", "Đang thẩm định"],
            ] as const
          ).map(([status, label]) => (
            <Link
              aria-label={`${label}: ${metrics.data.dossierFunnel[status] ?? 0} hồ sơ`}
              className="flex min-h-14 items-center justify-between gap-3 py-2.5 hover:text-[var(--theme-accent)] sm:min-h-24 sm:rounded-xl sm:border sm:border-[var(--theme-border)] sm:bg-[var(--theme-surface)] sm:p-4 sm:hover:border-primary-300"
              href={`/admin/reviews?status=${status}`}
              key={status}
            >
              <span className="text-sm font-bold">{label}</span>
              <strong className="text-xl tabular-nums sm:text-2xl">
                {metrics.data.dossierFunnel[status] ?? 0}
              </strong>
            </Link>
          ))}
        </section>
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

      <section className="hero-grid-surface relative overflow-hidden rounded-2xl bg-neutral-950 px-5 py-7 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:grid-cols-[1fr_auto] lg:items-end lg:px-10 lg:py-10">
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
        className="divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)] sm:grid sm:grid-cols-2 sm:gap-3 sm:divide-y-0 sm:border-0 xl:grid-cols-4"
        aria-label="Chỉ số cần theo dõi"
        id="hang-doi-xu-ly"
      >
        {cards.map(([label, value, Icon, href]) => (
          <Link
            aria-label={`${label}: ${value}`}
            className="group flex min-h-20 items-center gap-4 py-3 text-[var(--theme-text)] transition-colors hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] sm:min-h-36 sm:flex-col sm:items-stretch sm:justify-between sm:rounded-xl sm:border sm:border-[var(--theme-border)] sm:bg-[var(--theme-surface)] sm:p-5 sm:hover:border-[var(--theme-accent)]"
            href={href}
            key={label}
          >
            <div className="flex min-w-0 flex-1 items-center gap-4 sm:justify-between">
              <p className="w-12 shrink-0 text-3xl font-bold tracking-[-0.04em] tabular-nums sm:w-auto sm:text-4xl">
                {value}
              </p>
              <p className="min-w-0 flex-1 text-sm font-semibold leading-5 sm:hidden">
                {label}
              </p>
              <Icon
                aria-hidden="true"
                className="size-5 shrink-0 text-[var(--theme-accent)]"
              />
            </div>
            <span className="hidden items-center justify-between gap-2 text-sm font-semibold text-[var(--theme-muted)] sm:flex">
              {label}
              <ArrowUpRight
                aria-hidden="true"
                className="size-4 shrink-0 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              />
            </span>
            <ArrowUpRight
              aria-hidden="true"
              className="size-4 shrink-0 text-[var(--theme-muted)] sm:hidden"
            />
          </Link>
        ))}
      </section>

      {showHeader ? (
        <>
          <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
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
              <p className="text-xs text-neutral-500">
                Số hồ sơ đang hoạt động
              </p>
            </div>
            <div className="mt-6">
              <ReviewerWorkloadChart rows={metrics.data.reviewerWorkload} />
            </div>
          </section>
          <section className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
                  Hệ thống nền
                </p>
                <h2 className="mt-2 text-xl font-bold">Sức khỏe tác vụ</h2>
              </div>
              <p className="text-xs text-neutral-500">
                Hàng đợi lâu nhất:{" "}
                {Math.round(metrics.data.oldestQueuedJobAgeSeconds / 60)} phút
              </p>
            </div>
            <div className="mt-6">
              <OperationsJobHealthChart counts={metrics.data.jobStatusCounts} />
            </div>
          </section>
          {user?.roles.includes("SUPER_ADMIN") ? (
            <JobOperationsWorkspace />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
