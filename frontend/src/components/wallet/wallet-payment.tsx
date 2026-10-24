"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { ApiError, walletApi } from "@/lib/api/client";
import type { PaymentOrder } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { paymentKeys } from "@/lib/payments/query-keys";
import { formatVnd, walletKey } from "./wallet-workspace";

export function WalletPayment({ order }: { order: PaymentOrder }) {
  const user = useAuthUser();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [key] = useState(() => crypto.randomUUID());
  const queryKey = walletKey(user?.id);
  const balance = useQuery({
    queryKey,
    queryFn: walletApi.summary,
    staleTime: 0,
  });
  const pay = useMutation({
    mutationFn: () => walletApi.pay(order.id, key),
    onSuccess: async (paid) => {
      client.setQueryData(paymentKeys.detail(order.id), paid);
      await client.invalidateQueries({ queryKey });
      await client.invalidateQueries({ queryKey: ["dossiers"] });
      setOpen(false);
    },
  });
  if (balance.isPending) return <p role="status">Đang kiểm tra số dư ví…</p>;
  if (!balance.data)
    return (
      <div role="alert">
        <p>Chưa thể kiểm tra ví.</p>
        <Button variant="outline" onClick={() => void balance.refetch()}>
          Thử lại
        </Button>
      </div>
    );
  const missing = Math.max(0, order.amountMinor - balance.data.balanceMinor);
  return (
    <section
      aria-label="Thanh toán bằng ví"
      className="space-y-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5"
    >
      <h2 className="text-lg font-bold">Thanh toán bằng ví</h2>
      <p>
        Số dư khả dụng: <strong>{formatVnd(balance.data.balanceMinor)}</strong>
      </p>
      {missing > 0 ? (
        <>
          <p>
            Bạn cần nạp thêm <strong>{formatVnd(missing)}</strong> để thanh toán
            khoản phí này. Hồ sơ của bạn vẫn được lưu.
          </p>
          <Link
            className="inline-flex min-h-11 items-center font-semibold text-primary-700 underline"
            href={`/wallet?returnTo=${encodeURIComponent(`/payments/${order.id}`)}`}
          >
            Nạp tiền vào ví
          </Link>
        </>
      ) : (
        <Button onClick={() => setOpen(true)} disabled={pay.isPending}>
          Thanh toán {formatVnd(order.amountMinor)}
        </Button>
      )}
      <p className="text-sm text-[var(--theme-muted)]">
        Thanh toán phí không bảo đảm kết quả thẩm định chuyên môn.
      </p>
      <ConfirmationDialog
        open={open}
        title="Xác nhận thanh toán bằng ví"
        description={`Trừ ${formatVnd(order.amountMinor)} từ ví để thanh toán ${order.description || "phí hồ sơ"}.`}
        confirmLabel="Xác nhận thanh toán"
        onCancel={() => setOpen(false)}
        onConfirm={() => pay.mutate()}
        isPending={pay.isPending}
      >
        <p>
          Số dư sau thanh toán:{" "}
          {formatVnd(balance.data.balanceMinor - order.amountMinor)}
        </p>
        {pay.isError && (
          <p role="alert" className="mt-3 text-red-700">
            {pay.error instanceof ApiError
              ? pay.error.message
              : "Chưa thể xác nhận. Vui lòng kiểm tra trạng thái trước khi thử lại."}
          </p>
        )}
      </ConfirmationDialog>
    </section>
  );
}
