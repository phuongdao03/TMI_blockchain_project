"use client";

import { useMutation } from "@tanstack/react-query";
import { BadgeDollarSign, CheckCircle2, Clock3 } from "lucide-react";
import { useRouter } from "next/navigation";

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
  const createOrder = useMutation({
    mutationFn: () => paymentApi.create(dossierId, idempotencyKey()),
    onSuccess: (order) => router.push(`/thanh-toan/${order.id}`),
  });

  if (dossierStatus === "PAID") {
    return (
      <section className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-950">
        <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-bold">Phí xác lập đã được ghi nhận</h2>
          <p className="mt-1 text-sm leading-6 text-emerald-800">
            Hồ sơ đang sẵn sàng chuyển sang bước neo dữ liệu blockchain.
          </p>
        </div>
      </section>
    );
  }
  if (dossierStatus === "PAYMENT_PENDING") {
    return (
      <section className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950">
        <Clock3 aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-bold">Đang chờ xác nhận thanh toán</h2>
          <p className="mt-1 text-sm leading-6 text-amber-800">
            Chỉ webhook đã xác thực từ nhà cung cấp mới có thể đánh dấu đã trả.
          </p>
        </div>
      </section>
    );
  }
  if (dossierStatus !== "APPROVED") {
    return null;
  }

  return (
    <section className="grid gap-5 rounded-2xl border border-primary-200 bg-primary-50 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="flex items-start gap-3">
        <BadgeDollarSign
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-primary-700"
        />
        <div>
          <h2 className="font-bold text-primary-950">Hồ sơ đã được duyệt</h2>
          <p className="mt-1 text-sm leading-6 text-primary-900/75">
            Tạo lệnh thanh toán để tiếp tục quy trình xác lập và neo blockchain.
          </p>
        </div>
      </div>
      <Button
        disabled={createOrder.isPending}
        onClick={() => createOrder.mutate()}
      >
        {createOrder.isPending ? "Đang tạo lệnh…" : "Tạo lệnh thanh toán"}
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
