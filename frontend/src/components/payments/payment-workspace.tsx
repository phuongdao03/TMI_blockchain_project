"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clock3,
  ExternalLink,
  LoaderCircle,
  QrCode,
  ReceiptText,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { paymentApi } from "@/lib/api/client";
import type { PaymentOrder } from "@/lib/api/types";
import { paymentKeys } from "@/lib/payments/query-keys";

const POLLING_STATUSES = new Set(["PENDING", "PROCESSING"]);

function money(order: PaymentOrder) {
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

export function PaymentWorkspace({ orderId }: { orderId: string }) {
  const order = useQuery({
    queryKey: paymentKeys.detail(orderId),
    queryFn: () => paymentApi.get(orderId),
    refetchInterval: ({ state }) =>
      state.data && POLLING_STATUSES.has(state.data.status) ? 3_000 : false,
  });

  if (order.isPending) {
    return (
      <div
        aria-busy="true"
        className="grid min-h-[26rem] place-items-center rounded-2xl border border-neutral-200 bg-white"
      >
        <span className="flex items-center gap-3 font-semibold text-neutral-600">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang kiểm tra lệnh thanh toán…
        </span>
      </div>
    );
  }
  if (order.error || !order.data) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800"
        role="alert"
      >
        Không thể tải trạng thái thanh toán. Vui lòng quay lại hồ sơ và thử lại.
      </div>
    );
  }

  const payment = order.data;
  const paid = payment.status === "PAID";
  const stopped = ["FAILED", "EXPIRED", "REFUNDED"].includes(payment.status);

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-500 hover:text-primary-700"
        href={`/ho-so/${payment.dossierId}`}
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Quay lại hồ sơ
      </Link>

      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 bg-neutral-950 px-5 py-6 text-white sm:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs tracking-[0.16em] text-primary-300">
                {payment.orderCode}
              </p>
              <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
                {paid
                  ? "Thanh toán thành công"
                  : stopped
                    ? "Lệnh thanh toán đã dừng"
                    : "Xác nhận phí xác lập"}
              </h1>
            </div>
            <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold">
              {payment.status}
            </span>
          </div>
        </div>

        <div className="grid gap-8 p-5 sm:p-8 lg:grid-cols-[1fr_20rem]">
          <div className="space-y-6">
            <div>
              <p className="text-sm font-medium text-neutral-500">
                Số tiền cần thanh toán
              </p>
              <p className="mt-2 text-4xl font-bold tracking-[-0.04em] text-neutral-950">
                {money(payment)}
              </p>
              <p className="mt-2 text-sm text-neutral-500">
                Hết hạn lúc {formatTime(payment.expiresAt)}
              </p>
            </div>

            {paid ? (
              <div
                className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-950"
                role="status"
              >
                <CheckCircle2
                  aria-hidden="true"
                  className="mt-0.5 size-6 shrink-0"
                />
                <div>
                  <h2 className="font-bold">Biên nhận đã được xác thực</h2>
                  <p className="mt-1 text-sm leading-6 text-emerald-800">
                    Backend đã nhận webhook hợp lệ
                    {payment.paidAt ? ` lúc ${formatTime(payment.paidAt)}` : ""}
                    . Redirect từ nhà cung cấp không được dùng làm bằng chứng.
                  </p>
                </div>
              </div>
            ) : stopped ? (
              <div
                className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-5 text-red-900"
                role="alert"
              >
                <CircleAlert
                  aria-hidden="true"
                  className="mt-0.5 size-6 shrink-0"
                />
                <div>
                  <h2 className="font-bold">Không thể tiếp tục với lệnh này</h2>
                  <p className="mt-1 text-sm leading-6">
                    Trạng thái hiện tại: {payment.status}. Quay lại hồ sơ để
                    kiểm tra hoặc liên hệ bộ phận hỗ trợ.
                  </p>
                </div>
              </div>
            ) : (
              <div
                className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950"
                role="status"
              >
                <Clock3 aria-hidden="true" className="mt-0.5 size-6 shrink-0" />
                <div>
                  <h2 className="font-bold">Đang chờ nhà cung cấp xác nhận</h2>
                  <p className="mt-1 text-sm leading-6 text-amber-800">
                    Trang tự kiểm tra trạng thái mỗi 3 giây. Bạn có thể giữ
                    trang này mở sau khi hoàn tất thanh toán.
                  </p>
                </div>
              </div>
            )}

            {!paid && !stopped && payment.checkoutUrl ? (
              <a
                className={buttonVariants()}
                href={payment.checkoutUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Mở cổng thanh toán
                <ExternalLink aria-hidden="true" className="size-4" />
              </a>
            ) : null}
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
              {payment.qrPayload && !paid ? (
                <>
                  <QrCode
                    aria-hidden="true"
                    className="size-10 text-neutral-900"
                  />
                  <h2 className="mt-4 font-bold">Mã thanh toán</h2>
                  <p className="mt-2 break-all font-mono text-xs leading-5 text-neutral-500">
                    {payment.qrPayload}
                  </p>
                </>
              ) : (
                <>
                  <ReceiptText
                    aria-hidden="true"
                    className="size-10 text-neutral-900"
                  />
                  <h2 className="mt-4 font-bold">Thông tin biên nhận</h2>
                  <p className="mt-2 text-sm leading-6 text-neutral-500">
                    Nhà cung cấp: {payment.provider}
                  </p>
                </>
              )}
            </div>
            <div className="flex gap-3 rounded-2xl border border-neutral-200 p-4 text-sm text-neutral-600">
              <ShieldCheck
                aria-hidden="true"
                className="size-5 shrink-0 text-primary-700"
              />
              Không lưu dữ liệu thẻ. Số tiền và loại tiền được khóa tại thời
              điểm tạo lệnh.
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
