"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, Clock3, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { paymentApi } from "@/lib/api/client";
import type { AdminPaymentOrder, PaymentStatus } from "@/lib/api/types";

const paymentListKey = ["admin", "payment-orders"] as const;
const pendingStatuses = new Set<PaymentStatus>(["PENDING", "PROCESSING"]);

const statusLabels: Record<PaymentStatus, string> = {
  PENDING: "Chờ thanh toán",
  PROCESSING: "Đang xác nhận",
  PAID: "Đã thanh toán",
  FAILED: "Chưa thành công",
  CANCELLED: "Đã hủy",
  EXPIRED: "Đã hết hạn",
  REFUNDED: "Đã hoàn tiền",
};

function formatMoney(order: AdminPaymentOrder["order"]) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: order.currency,
    maximumFractionDigits: 0,
  }).format(order.amountMinor);
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function PaymentOrderReconciliation() {
  const queryClient = useQueryClient();
  const orders = useQuery({
    queryKey: paymentListKey,
    queryFn: paymentApi.listAdminOrders,
    refetchInterval: ({ state }) =>
      state.data?.some(({ order }) => pendingStatuses.has(order.status))
        ? 10_000
        : false,
  });
  const reconcile = useMutation({
    mutationFn: paymentApi.reconcile,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: paymentListKey });
    },
  });

  return (
    <section
      aria-labelledby="payment-reconciliation-title"
      className="space-y-4 rounded-3xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2
            className="text-xl font-bold tracking-tight text-[var(--theme-text)]"
            id="payment-reconciliation-title"
          >
            Theo dõi thu phí
          </h2>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            Trạng thái thanh toán đã được hệ thống xác nhận, kèm thời điểm ghi
            nhận.
          </p>
        </div>
        <Button
          className="min-h-10 px-3 text-sm"
          onClick={() => void orders.refetch()}
          variant="outline"
        >
          <RefreshCw aria-hidden="true" className="size-4" />
          Làm mới
        </Button>
      </div>

      {orders.isPending ? (
        <p aria-busy="true" className="py-4 text-sm text-[var(--theme-muted)]">
          Đang tải các khoản thu…
        </p>
      ) : orders.isError ? (
        <div className="rounded-xl border border-red-300 p-4" role="alert">
          <p className="text-sm">Chưa tải được danh sách thu phí.</p>
          <button
            className="mt-2 min-h-11 font-bold underline"
            onClick={() => void orders.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      ) : orders.data.length === 0 ? (
        <p className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 text-sm text-[var(--theme-muted)]">
          Chưa có khoản thu nào được tạo.
        </p>
      ) : (
        <ul className="divide-y divide-[var(--theme-border)]">
          {orders.data.map(({ order, dossierCode, dossierTitle }) => {
            const paid = order.status === "PAID";
            const canReconcile = pendingStatuses.has(order.status);

            return (
              <li
                className="flex flex-col gap-3 py-4 first:pt-1 last:pb-1 sm:flex-row sm:items-center sm:justify-between"
                key={order.id}
              >
                <div className="min-w-0 space-y-1">
                  <p className="truncate font-semibold text-[var(--theme-text)]">
                    {dossierCode} · {dossierTitle}
                  </p>
                  <p className="text-sm text-[var(--theme-muted)]">
                    {order.orderCode} · {formatMoney(order)}
                  </p>
                  <p className="flex items-center gap-1.5 text-xs text-[var(--theme-muted)]">
                    {paid ? (
                      <CheckCircle2
                        aria-hidden="true"
                        className="size-3.5 text-emerald-600"
                      />
                    ) : (
                      <Clock3 aria-hidden="true" className="size-3.5" />
                    )}
                    {paid && order.paidAt
                      ? `Đã ghi nhận lúc ${formatTime(order.paidAt)}`
                      : `Tạo lúc ${formatTime(order.createdAt)}`}
                  </p>
                </div>

                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <span
                    className={`inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 text-xs font-bold ${
                      paid
                        ? "border-emerald-700/30 bg-emerald-700/10 text-emerald-800 dark:text-emerald-300"
                        : "border-[var(--theme-border)] bg-[var(--theme-elevated)] text-[var(--theme-text)]"
                    }`}
                  >
                    {paid ? (
                      <CheckCircle2 aria-hidden="true" className="size-4" />
                    ) : null}
                    {statusLabels[order.status]}
                  </span>
                  {canReconcile ? (
                    <Button
                      className="min-h-10 px-3 text-sm"
                      disabled={reconcile.isPending}
                      onClick={() => reconcile.mutate(order.id)}
                      variant="outline"
                    >
                      <RefreshCw
                        aria-hidden="true"
                        className={`size-4 ${reconcile.isPending ? "animate-spin" : ""}`}
                      />
                      Đối soát
                    </Button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {reconcile.isError ? (
        <p
          className="flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm"
          role="alert"
        >
          <CircleAlert aria-hidden="true" className="size-4 shrink-0" />
          Chưa đối soát được khoản thu. Vui lòng thử lại.
        </p>
      ) : null}
    </section>
  );
}
