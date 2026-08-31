"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { BadgeDollarSign, CheckCircle2, Clock3, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { paymentApi } from "@/lib/api/client";
import type { DossierStatus } from "@/lib/api/types";

export function DossierPaymentAction({
  dossierId,
  dossierStatus,
}: {
  dossierId: string;
  dossierStatus: DossierStatus;
}) {
  const router = useRouter();
  const shouldLoadPayment = dossierStatus === "PAYMENT_PENDING";
  const obligation = useQuery({
    queryKey: ["fee-obligation", dossierId],
    queryFn: () => paymentApi.getFeeObligation(dossierId),
    enabled: shouldLoadPayment,
    retry: false,
  });
  const activeOrder = useQuery({
    queryKey: ["active-payment-order", dossierId],
    queryFn: () => paymentApi.getActive(dossierId),
    enabled: shouldLoadPayment,
    retry: false,
  });
  const checkout = useMutation({
    mutationFn: (obligationId: string) =>
      paymentApi.createCheckout(obligationId, crypto.randomUUID()),
    onSuccess: (order) => router.push(`/payments/${order.id}`),
  });

  if (dossierStatus === "PAID") {
    return (
      <section className="dossier-payment-notice dossier-payment-notice--success flex items-start gap-3 rounded-2xl p-5">
        <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-bold">Thanh toán đã được xác nhận</h2>
          <p className="mt-1 text-sm leading-6">
            Hồ sơ đang ở hàng đợi ký blockchain và phát hành chứng thư.
          </p>
        </div>
      </section>
    );
  }

  if (dossierStatus === "PAYMENT_PENDING") {
    return (
      <section className="dossier-payment-notice dossier-payment-notice--pending flex items-start gap-3 rounded-2xl p-5">
        <Clock3 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div className="min-w-0">
          <h2 className="font-bold">Yêu cầu thanh toán đã được gửi</h2>
          {activeOrder.data ? (
            <>
              <p className="mt-1 text-sm leading-6">
                Số tiền: {new Intl.NumberFormat("vi-VN").format(activeOrder.data.amountMinor)} VND
                {activeOrder.data.description ? ` · ${activeOrder.data.description}` : ""}
              </p>
              <Link
                className="dossier-payment-notice__link mt-3 inline-flex min-h-11 items-center text-sm font-bold underline decoration-2 underline-offset-4"
                href={`/payments/${activeOrder.data.id}`}
              >
                Xem và thanh toán qua PayOS
              </Link>
            </>
          ) : obligation.data ? (
            <>
              <p className="mt-1 text-sm leading-6">
                <strong>
                  {new Intl.NumberFormat("vi-VN").format(obligation.data.amountMinor)}{" "}
                  {obligation.data.currency}
                </strong>{" "}
                · {obligation.data.description}
              </p>
              <p className="mt-1 text-xs leading-5 opacity-80">
                Hạn thanh toán {new Intl.DateTimeFormat("vi-VN", {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(obligation.data.dueAt))}. Phiên QR PayOS được tạo khi bạn
                bắt đầu thanh toán và có thể cấp lại an toàn nếu hết hạn.
              </p>
              <button
                className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={checkout.isPending}
                onClick={() => checkout.mutate(obligation.data.id)}
                type="button"
              >
                {checkout.isPending ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : (
                  <BadgeDollarSign aria-hidden="true" className="size-4" />
                )}
                {checkout.isPending ? "Đang mở PayOS…" : "Thanh toán qua PayOS"}
              </button>
              {checkout.isError ? (
                <p className="mt-2 text-sm font-semibold text-red-700" role="alert">
                  Chưa thể tạo phiên thanh toán. Vui lòng thử lại; hệ thống sẽ không tạo trùng
                  giao dịch.
                </p>
              ) : null}
            </>
          ) : activeOrder.isPending || obligation.isPending ? (
            <p className="mt-2 flex items-center gap-2 text-sm font-semibold">
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
              Đang tải khoản phí…
            </p>
          ) : (
            <p className="mt-2 text-sm font-semibold" role="alert">
              Khoản phí chưa sẵn sàng. Vui lòng tải lại hoặc liên hệ hỗ trợ và cung cấp mã hồ sơ.
            </p>
          )}
        </div>
      </section>
    );
  }

  if (dossierStatus !== "APPROVED") return null;

  return (
    <section className="dossier-payment-notice dossier-payment-notice--action rounded-2xl p-5">
      <div className="flex items-start gap-3">
        <BadgeDollarSign
          aria-hidden="true"
          className="dossier-payment-notice__icon mt-0.5 size-5 shrink-0"
        />
        <div>
          <h2 className="font-bold">Hồ sơ đã được phê duyệt</h2>
          <p className="mt-1 text-sm leading-6">
            Bộ phận quản trị đang xác định mức phí. Khi yêu cầu được phát hành,
            bạn sẽ nhận thông báo kèm số tiền và liên kết PayOS.
          </p>
        </div>
      </div>
    </section>
  );
}
