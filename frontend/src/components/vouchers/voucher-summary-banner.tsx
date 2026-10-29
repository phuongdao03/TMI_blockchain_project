"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { voucherApi } from "@/lib/api/client";
import { formatVnd } from "@/lib/wallet/summary";

export function VoucherSummaryBanner({ userId }: { userId: string }) {
  const vouchers = useQuery({
    queryKey: ["vouchers", "mine", userId],
    queryFn: voucherApi.mine,
    staleTime: 60_000,
  });
  const available = vouchers.data?.find(
    (voucher) =>
      !voucher.expired && (!voucher.status || voucher.status === "AVAILABLE"),
  );
  if (!available) return null;
  return (
    <aside className="mx-5 my-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm text-[var(--theme-text)]">
      <span>
        Bạn đang có ưu đãi{" "}
        {available.policy?.discountType === "PERCENT"
          ? `${available.policy.percentageBps / 100}%`
          : formatVnd(available.amountVnd)}
        .
      </span>
      <Link
        className="font-semibold underline underline-offset-4"
        href="/vouchers"
      >
        Xem ưu đãi
      </Link>
    </aside>
  );
}
