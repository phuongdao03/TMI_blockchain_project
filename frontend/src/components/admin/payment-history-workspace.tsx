"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw, Search } from "lucide-react";
import { useState } from "react";

import { paymentApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type { PaymentHistoryFilters, PaymentStatus } from "@/lib/api/types";
import { Button } from "@/components/ui/button";

const statuses: Array<{ value: PaymentStatus | ""; label: string }> = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "PENDING", label: "Chờ thanh toán" },
  { value: "PROCESSING", label: "Đang xác nhận" },
  { value: "PAID", label: "Đã thanh toán" },
  { value: "FAILED", label: "Chưa thành công" },
  { value: "CANCELLED", label: "Đã hủy" },
  { value: "EXPIRED", label: "Đã hết hạn" },
  { value: "REFUNDED", label: "Đã hoàn tiền" },
];

const statusLabels = Object.fromEntries(
  statuses
    .filter(({ value }) => value)
    .map(({ value, label }) => [value, label]),
) as Record<PaymentStatus, string>;

const historySourceLabels: Record<string, string> = {
  ORDER_CREATED: "Tạo giao dịch",
  CHECKOUT_CREATED: "Tạo yêu cầu thanh toán",
  REQUEST_ISSUED: "Gửi yêu cầu thu phí",
  CHECKOUT_READY: "Tạo mã thanh toán",
  CANCELLED_BY_USER: "Người nộp hủy",
  WEBHOOK: "Cập nhật từ PayOS",
  RECONCILIATION: "Đối soát",
  MANUAL_CONFIRMATION: "Xác nhận thủ công",
  EXPIRY: "Hết hạn",
};

function money(amount: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function dateStart(value: string) {
  return value ? new Date(`${value}T00:00:00`).toISOString() : undefined;
}

function dateEnd(value: string) {
  return value ? new Date(`${value}T23:59:59.999`).toISOString() : undefined;
}

export function PaymentHistoryWorkspace() {
  const user = useAuthUser();
  const canExport =
    user?.roles.includes("SUPER_ADMIN") ||
    user?.permissions?.includes("payments.export");
  const [filters, setFilters] = useState<PaymentHistoryFilters>({
    page: 1,
    pageSize: 25,
  });
  const [searchDraft, setSearchDraft] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(false);

  const history = useQuery({
    queryKey: ["admin", "payment-history", filters],
    queryFn: () => paymentApi.listHistory(filters),
  });
  const detail = useQuery({
    queryKey: ["admin", "payment-history-detail", selectedOrderId],
    queryFn: () => paymentApi.getAdminHistoryDetail(selectedOrderId ?? ""),
    enabled: Boolean(selectedOrderId),
  });

  const applyFilters = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFilters((current) => ({
      ...current,
      page: 1,
      query: searchDraft.trim() || undefined,
      createdFrom: dateStart(dateFrom),
      createdTo: dateEnd(dateTo),
    }));
  };

  const exportCsv = async () => {
    setExporting(true);
    setExportError(false);
    try {
      const file = await paymentApi.exportHistory(filters);
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = "payment-history.csv";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setExportError(true);
    } finally {
      setExporting(false);
    }
  };

  const pageData = history.data?.data;
  const total = history.data?.meta.total ?? 0;
  const page = filters.page ?? 1;
  const pageSize = filters.pageSize ?? 25;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="mx-auto max-w-7xl space-y-6 pb-12">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          Tài chính
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)]">
          Lịch sử thanh toán
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
          Tra cứu giao dịch, người nộp hồ sơ, tài khoản khởi tạo và các lần đổi
          trạng thái.
        </p>
      </header>

      {pageData ? (
        <div className="space-y-3">
          <section
            aria-label="Thống kê thanh toán"
            className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
          >
            <SummaryCard
              label="Giao dịch trong kết quả"
              value={String(pageData.summary.total)}
            />
            <SummaryCard
              label="Đã thanh toán"
              value={String(pageData.summary.statusCounts.PAID ?? 0)}
            />
            <SummaryCard
              label="Tiền đã ghi nhận"
              value={money(pageData.summary.paidAmountMinor)}
            />
            <SummaryCard
              label="Tổng giá trị"
              value={money(pageData.summary.totalAmountMinor)}
            />
          </section>
          <section
            aria-label="Số giao dịch theo trạng thái trong kết quả"
            className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7"
          >
            {statuses
              .filter(({ value }) => value)
              .map(({ value, label }) => (
                <div
                  className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-2"
                  key={value}
                >
                  <p className="text-xs text-[var(--theme-muted)]">{label}</p>
                  <p className="mt-1 font-bold text-[var(--theme-text)]">
                    {pageData.summary.statusCounts[value as PaymentStatus] ?? 0}
                  </p>
                </div>
              ))}
          </section>
        </div>
      ) : null}

      <section className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
        <form
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(14rem,1fr)_12rem_12rem_12rem_auto_auto]"
          onSubmit={applyFilters}
        >
          <label className="sm:col-span-2 xl:col-span-1">
            <span className="mb-1 block text-xs font-bold text-[var(--theme-muted)]">
              Tìm giao dịch
            </span>
            <input
              className="min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)]"
              maxLength={120}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Mã giao dịch, hồ sơ hoặc email"
              value={searchDraft}
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-bold text-[var(--theme-muted)]">
              Trạng thái
            </span>
            <select
              className="min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)]"
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  page: 1,
                  status: (event.target.value || undefined) as
                    | PaymentStatus
                    | undefined,
                }))
              }
              value={filters.status ?? ""}
            >
              {statuses.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-bold text-[var(--theme-muted)]">
              Từ ngày
            </span>
            <input
              className="min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm"
              onChange={(event) => setDateFrom(event.target.value)}
              type="date"
              value={dateFrom}
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-bold text-[var(--theme-muted)]">
              Đến ngày
            </span>
            <input
              className="min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm"
              onChange={(event) => setDateTo(event.target.value)}
              type="date"
              value={dateTo}
            />
          </label>
          <Button className="min-h-11 self-end" type="submit">
            <Search aria-hidden="true" className="size-4" />
            Lọc
          </Button>
          {canExport ? (
            <Button
              className="min-h-11 self-end"
              disabled={exporting}
              onClick={() => void exportCsv()}
              type="button"
              variant="outline"
            >
              <Download aria-hidden="true" className="size-4" />
              {exporting ? "Đang xuất…" : "Xuất CSV"}
            </Button>
          ) : null}
        </form>
        {exportError ? (
          <p className="text-sm text-red-700" role="alert">
            Không xuất được tệp. Hãy thử lại.
          </p>
        ) : null}

        {history.isPending ? (
          <p
            aria-busy="true"
            className="py-8 text-center text-sm text-[var(--theme-muted)]"
            role="status"
          >
            Đang tải lịch sử thanh toán…
          </p>
        ) : history.isError ? (
          <div className="rounded-xl border border-red-300 p-4" role="alert">
            <p>Không tải được lịch sử thanh toán.</p>
            <button
              className="mt-2 min-h-11 font-bold underline"
              onClick={() => void history.refetch()}
              type="button"
            >
              Thử tải lại
            </button>
          </div>
        ) : pageData?.rows.length ? (
          <ul className="divide-y divide-[var(--theme-border)]">
            {pageData.rows.map((row) => (
              <li className="py-4 first:pt-1 last:pb-1" key={row.order.id}>
                <article className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                  <div className="min-w-0 space-y-1">
                    <p className="font-semibold text-[var(--theme-text)]">
                      {row.dossierCode} · {row.dossierTitle}
                    </p>
                    <p className="break-all font-mono text-sm text-[var(--theme-muted)]">
                      {row.order.orderCode} · {money(row.order.amountMinor)}
                    </p>
                    <p className="text-sm text-[var(--theme-muted)]">
                      Người nộp: {row.applicantEmail}
                    </p>
                    <p className="text-sm text-[var(--theme-muted)]">
                      Khởi tạo:{" "}
                      {row.initiatedByEmail ??
                        "Chưa có dữ liệu tài khoản khởi tạo"}
                    </p>
                    <p className="text-xs text-[var(--theme-muted)]">
                      Tạo lúc {formatDate(row.order.createdAt)} ·{" "}
                      {row.order.paidAt
                        ? `Thanh toán ${formatDate(row.order.paidAt)}`
                        : "Chưa ghi nhận thanh toán"}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                    <span className="inline-flex min-h-9 items-center rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 text-xs font-bold text-[var(--theme-text)]">
                      {statusLabels[row.order.status]}
                    </span>
                    <Button
                      className="min-h-11"
                      onClick={() =>
                        setSelectedOrderId(
                          selectedOrderId === row.order.id
                            ? null
                            : row.order.id,
                        )
                      }
                      type="button"
                      variant="outline"
                    >
                      {selectedOrderId === row.order.id
                        ? "Ẩn chi tiết"
                        : "Chi tiết"}
                    </Button>
                  </div>
                </article>
                {selectedOrderId === row.order.id ? (
                  <HistoryDetail
                    detail={detail.data}
                    isError={detail.isError}
                    isPending={detail.isPending}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-8 text-center text-sm text-[var(--theme-muted)]">
            Không tìm thấy giao dịch phù hợp.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--theme-border)] pt-4 text-sm">
          <p className="text-[var(--theme-muted)]">
            {total} giao dịch · Trang {page}/{totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              className="min-h-11"
              disabled={page <= 1 || history.isFetching}
              onClick={() =>
                setFilters((current) => ({ ...current, page: page - 1 }))
              }
              type="button"
              variant="outline"
            >
              Trước
            </Button>
            <Button
              className="min-h-11"
              disabled={page >= totalPages || history.isFetching}
              onClick={() =>
                setFilters((current) => ({ ...current, page: page + 1 }))
              }
              type="button"
              variant="outline"
            >
              Sau
            </Button>
            <Button
              aria-label="Làm mới lịch sử"
              className="min-h-11"
              disabled={history.isFetching}
              onClick={() => void history.refetch()}
              type="button"
              variant="outline"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
      <p className="text-xs font-bold text-[var(--theme-muted)]">{label}</p>
      <p className="mt-2 break-words text-xl font-bold text-[var(--theme-text)]">
        {value}
      </p>
    </div>
  );
}

function HistoryDetail({
  detail,
  isError,
  isPending,
}: {
  detail:
    | Awaited<ReturnType<typeof paymentApi.getAdminHistoryDetail>>
    | undefined;
  isError: boolean;
  isPending: boolean;
}) {
  if (isPending)
    return (
      <p aria-busy="true" className="mt-4 text-sm">
        Đang tải chi tiết…
      </p>
    );
  if (isError || !detail)
    return (
      <p className="mt-4 text-sm text-red-700" role="alert">
        Không tải được chi tiết giao dịch.
      </p>
    );

  return (
    <div className="mt-4 grid gap-5 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 lg:grid-cols-2">
      <div className="space-y-2 text-sm">
        <h3 className="font-bold">Thông tin hồ sơ và giao dịch</h3>
        <p>Người đứng tên hồ sơ: {detail.row.applicantEmail}</p>
        <p>
          Tài khoản khởi tạo:{" "}
          {detail.row.initiatedByEmail ?? "Chưa có dữ liệu tài khoản khởi tạo"}
        </p>
        <p>Mô tả: {detail.row.order.description || "—"}</p>
        <p>Hạn thanh toán: {formatDate(detail.row.order.dueAt ?? null)}</p>
      </div>
      <div>
        <h3 className="font-bold">Lịch sử trạng thái</h3>
        {detail.statusHistory.length ? (
          <ol className="mt-2 space-y-2">
            {detail.statusHistory.map((item) => (
              <li
                className="border-l-2 border-[var(--theme-border)] pl-3 text-sm"
                key={item.id}
              >
                <p className="font-semibold">
                  {item.fromStatus
                    ? (statusLabels[item.fromStatus as PaymentStatus] ??
                      item.fromStatus)
                    : "Khởi tạo"}{" "}
                  →{" "}
                  {statusLabels[item.toStatus as PaymentStatus] ??
                    item.toStatus}
                </p>
                <p className="text-xs text-[var(--theme-muted)]">
                  {formatDate(item.changedAt)} ·{" "}
                  {historySourceLabels[item.source] ?? item.source} ·{" "}
                  {item.actorEmail ?? "Hệ thống"}
                </p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-2 text-sm text-[var(--theme-muted)]">
            Chưa ghi nhận lịch sử chuyển trạng thái cho giao dịch cũ.
          </p>
        )}
      </div>
    </div>
  );
}
