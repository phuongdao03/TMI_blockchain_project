"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { formatVnd } from "@/lib/wallet/summary";
import { paymentKeys } from "@/lib/payments/query-keys";

type Quote = {
  originalVnd: number;
  membershipDiscountVnd: number;
  recommendedVoucherId: string | null;
  selectedVoucherId?: string | null;
  currentPayableVnd?: number;
  vouchers: {
    voucherId: string;
    title: string;
    discountVnd: number;
    payableVnd: number;
  }[];
};

export function CheckoutVoucherSelector({
  serviceCode,
  resourceId,
  selectedId,
  onSelect,
  renewalOptIn = false,
  order = false,
}: {
  serviceCode:
    | "DOSSIER_SUBMISSION"
    | "DOSSIER_APPROVAL"
    | "MEMBERSHIP"
    | "ADVERTISING";
  resourceId: string;
  selectedId?: string | null;
  onSelect?: (id: string | null) => void;
  renewalOptIn?: boolean;
  order?: boolean;
}) {
  const user = useAuthUser();
  const client = useQueryClient();
  const eligible = Boolean(
    user &&
      !user.isEmployee &&
      user.roles?.length > 0 &&
      user.roles.every((role) => role === "USER"),
  );
  const queryKey = [
    "voucher-checkout",
    user?.id,
    serviceCode,
    resourceId,
    renewalOptIn,
  ];
  const quote = useQuery({
    queryKey,
    enabled: eligible,
    queryFn: () =>
      request<Quote>("/checkout-vouchers/quote", {
        method: "POST",
        body: JSON.stringify({ serviceCode, resourceId, renewalOptIn }),
      }),
    retry: false,
  });
  const apply = useMutation({
    mutationFn: (voucherId: string | null) =>
      request(`/payment-orders/${encodeURIComponent(resourceId)}/voucher`, {
        method: "POST",
        body: JSON.stringify({ voucherId }),
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey });
      await client.invalidateQueries({
        queryKey: paymentKeys.detail(resourceId),
      });
      await client.invalidateQueries({
        queryKey: ["vouchers", "mine", user?.id],
      });
    },
  });
  if (!eligible) return null;
  const value = order
    ? (quote.data?.selectedVoucherId ?? "")
    : (selectedId ?? "");
  return (
    <section className="space-y-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 text-sm">
      <label className="grid gap-2 font-semibold">
        Ưu đãi có thể sử dụng
        <select
          aria-label="Chọn voucher thanh toán"
          value={value}
          disabled={!quote.data || apply.isPending}
          className="min-h-11 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-[var(--theme-text)]"
          onChange={(event) => {
            const id = event.target.value || null;
            if (order) apply.mutate(id);
            else onSelect?.(id);
          }}
        >
          <option value="">Không sử dụng voucher</option>
          {quote.data?.vouchers.map((voucher) => (
            <option key={voucher.voucherId} value={voucher.voucherId}>
              {voucher.title} · giảm {formatVnd(voucher.discountVnd)}
              {voucher.voucherId === quote.data?.recommendedVoucherId
                ? " · Gợi ý tốt nhất"
                : ""}
            </option>
          ))}
          {order &&
            value &&
            !quote.data?.vouchers.some((item) => item.voucherId === value) && (
              <option value={value}>Voucher đang được giữ cho đơn này</option>
            )}
        </select>
      </label>
      {quote.isPending && <p role="status">Đang tìm ưu đãi phù hợp…</p>}
      {(quote.isError || apply.isError) && (
        <p role="alert">
          {(apply.error ?? quote.error) instanceof Error
            ? (apply.error ?? quote.error)?.message
            : "Chưa thể kiểm tra ưu đãi. Vui lòng thử lại."}
        </p>
      )}
      {quote.data && !quote.data.vouchers.length && !value && (
        <p className="text-[var(--theme-muted)]">
          Chưa có voucher phù hợp với dịch vụ và điều kiện đơn hàng này.
        </p>
      )}
      {quote.data && (
        <p className="text-[var(--theme-muted)]">
          Giá và mức giảm được kiểm tra bởi hệ thống khi thanh toán. Voucher
          không cộng dồn với voucher khác.
        </p>
      )}
    </section>
  );
}
