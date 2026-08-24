"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { BadgeDollarSign, CheckCircle2, Clock3 } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { paymentApi } from "@/lib/api/client";
import type { DossierStatus } from "@/lib/api/types";

function idempotencyKey() {
  return globalThis.crypto?.randomUUID?.() ?? `payment-${Date.now()}`;
}

export function DossierPaymentAction({
  dossierId,
  dossierStatus,
}: {
  dossierId: string;
  dossierStatus: DossierStatus;
}) {
  const router = useRouter();
  const requestKey = useRef(idempotencyKey());
  const activeOrder = useQuery({
    queryKey: ["active-payment-order", dossierId],
    queryFn: () => paymentApi.getActive(dossierId),
    enabled: dossierStatus === "PAYMENT_PENDING",
    retry: false,
  });
  const createOrder = useMutation({
    mutationFn: () => paymentApi.create(dossierId, requestKey.current),
    onSuccess: (order) => router.push(`/payments/${order.id}`),
  });

  if (dossierStatus === "PAID") {
    return (
      <section className="dossier-payment-notice dossier-payment-notice--success flex items-start gap-3 rounded-2xl p-5">
        <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-bold">Phí xác lập đã được ghi nhận</h2>
          <p className="mt-1 text-sm leading-6 text-emerald-800">
            Hồ sơ đang được chuẩn bị để phát hành chứng thư.
          </p>
        </div>
      </section>
    );
  }
  if (dossierStatus === "PAYMENT_PENDING") {
    return (
      <section className="dossier-payment-notice dossier-payment-notice--pending flex items-start gap-3 rounded-2xl p-5">
        <Clock3 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-bold">Đang chờ xác nhận thanh toán</h2>
          <p className="mt-1 text-sm leading-6 text-amber-800">
            Bạn có thể mở lại trang thanh toán để tiếp tục hoặc chờ hệ thống cập
            nhật.
          </p>
          {activeOrder.data ? (
            <Link
              className="dossier-payment-notice__link mt-3 inline-flex min-h-11 items-center text-sm font-bold underline decoration-2 underline-offset-4"
              href={`/payments/${activeOrder.data.id}`}
            >
              Mở lại trang thanh toán
            </Link>
          ) : activeOrder.isPending ? (
            <p className="mt-3 text-sm font-semibold">
              Đang tìm lần thanh toán gần nhất…
            </p>
          ) : (
            <p className="mt-3 text-sm font-semibold">
              Chưa thể mở lại. Vui lòng tải lại trang hoặc liên hệ hỗ trợ.
            </p>
          )}
        </div>
      </section>
    );
  }
  if (dossierStatus !== "APPROVED") {
    return null;
  }

  return (
    <section className="dossier-payment-notice dossier-payment-notice--action grid gap-5 rounded-2xl p-5 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="flex items-start gap-3">
        <BadgeDollarSign
          aria-hidden="true"
          className="dossier-payment-notice__icon mt-0.5 size-5 shrink-0"
        />
        <div>
          <h2 className="font-bold text-primary-950">Hồ sơ đã được duyệt</h2>
          <p className="mt-1 text-sm leading-6 text-primary-900/75">
            Thanh toán phí phát hành để tiếp tục nhận chứng thư.
          </p>
        </div>
      </div>
      <Button
        disabled={createOrder.isPending}
        onClick={() => createOrder.mutate()}
      >
        {createOrder.isPending ? "Đang chuẩn bị…" : "Thanh toán phí phát hành"}
      </Button>
      {createOrder.error ? (
        <p
          className="text-sm font-medium text-red-700 sm:col-span-2"
          role="alert"
        >
          Không thể tạo lệnh thanh toán. Vui lòng tải lại hồ sơ và thử lại.
        </p>
      ) : null}
    </section>
  );
}
