"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleAlert, LoaderCircle } from "lucide-react";

import { PaymentWorkspace } from "@/components/payments/payment-workspace";
import { paymentApi } from "@/lib/api/client";

export function PaymentReturnWorkspace({
  providerOrderId,
}: {
  providerOrderId?: string;
}) {
  const order = useQuery({
    queryKey: ["payment-return", providerOrderId],
    queryFn: () => paymentApi.getByProviderReference(providerOrderId ?? ""),
    enabled: Boolean(providerOrderId),
    retry: 2,
  });

  if (!providerOrderId) {
    return (
      <div
        className="mx-auto max-w-2xl rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950"
        role="alert"
      >
        <CircleAlert aria-hidden="true" className="size-6" />
        <h1 className="mt-4 text-xl font-bold">Thiếu thông tin thanh toán</h1>
        <p className="mt-2 text-sm leading-6">
          Hãy quay lại hồ sơ và mở lần thanh toán gần nhất để tiếp tục.
        </p>
      </div>
    );
  }
  if (order.isPending) {
    return (
      <div
        className="flex min-h-80 items-center justify-center gap-3 text-sm font-semibold text-neutral-600"
        role="status"
      >
        <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        Đang kiểm tra trạng thái thanh toán…
      </div>
    );
  }
  if (order.isError || !order.data) {
    return (
      <div
        className="mx-auto max-w-2xl rounded-2xl border border-red-200 bg-red-50 p-6 text-red-900"
        role="alert"
      >
        <h1 className="text-xl font-bold">Chưa thể kiểm tra thanh toán</h1>
        <p className="mt-2 text-sm leading-6">
          Trạng thái trên trình duyệt chưa phải kết quả cuối cùng. Vui lòng mở
          lại hồ sơ hoặc thử lại sau ít phút.
        </p>
      </div>
    );
  }
  return <PaymentWorkspace orderId={order.data.id} />;
}
