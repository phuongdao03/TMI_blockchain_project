"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { voucherApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type { SavedVoucher } from "@/lib/api/voucher-types";
import { VoucherCard } from "./voucher-card";

type VoucherTab = "AVAILABLE" | "LOCKED" | "REDEEMED" | "EXPIRED";
export function voucherTab(voucher: SavedVoucher, now: number): VoucherTab {
  if (voucher.status === "REDEEMED") return "REDEEMED";
  if (voucher.expired) return "EXPIRED";
  if (
    voucher.status === "REVOKED" ||
    voucher.status === "RESERVED" ||
    (voucher.validFrom && Date.parse(voucher.validFrom) > now)
  )
    return "LOCKED";
  return "AVAILABLE";
}
export function VoucherWallet() {
  const user = useAuthUser();
  const client = useQueryClient();
  const [tab, setTab] = useState<VoucherTab>("AVAILABLE");
  const [code, setCode] = useState("");
  const [now] = useState(() => Date.now());
  const vouchers = useQuery({
    queryKey: ["vouchers", "mine", user?.id],
    queryFn: voucherApi.mine,
    enabled: Boolean(user),
  });
  const redeem = useMutation({
    mutationFn: () => voucherApi.redeemCode(code.trim().toUpperCase()),
    onSuccess: async () => {
      setCode("");
      await client.invalidateQueries({
        queryKey: ["vouchers", "mine", user?.id],
      });
    },
  });
  const selected =
    vouchers.data?.filter((voucher) => voucherTab(voucher, now) === tab) ?? [];
  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-widest text-[var(--theme-muted)]">
          Ưu đãi dành cho bạn
        </p>
        <h1 className="mt-2 text-2xl font-bold text-[var(--theme-text)]">
          Voucher của tôi
        </h1>
        <p className="mt-2 text-sm text-[var(--theme-muted)]">
          Mỗi ưu đãi được lưu theo tài khoản. Voucher không phải số dư ví và
          không quy đổi thành tiền mặt.
        </p>
      </header>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          redeem.mutate();
        }}
      >
        <label className="grid flex-1 gap-2 text-sm text-[var(--theme-text)]">
          <span>Bạn có mã khuyến mại?</span>
          <input
            className="min-h-11 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
            aria-label="Mã khuyến mại"
            minLength={3}
            maxLength={64}
            required
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />
        </label>
        <Button
          type="submit"
          disabled={redeem.isPending || code.trim().length < 3}
        >
          {redeem.isPending ? "Đang kiểm tra…" : "Nhận bằng mã"}
        </Button>
      </form>
      {redeem.isError && (
        <p role="alert" className="text-sm text-red-700">
          {redeem.error instanceof Error
            ? redeem.error.message
            : "Không thể nhận mã. Vui lòng kiểm tra điều kiện."}
        </p>
      )}
      {redeem.isSuccess && (
        <p role="status" className="text-sm text-green-700">
          Đã lưu ưu đãi vào tài khoản.
        </p>
      )}
      <div
        role="tablist"
        aria-label="Trạng thái voucher"
        className="flex gap-2 overflow-x-auto border-b border-[var(--theme-border)] pb-2"
      >
        {(
          [
            ["AVAILABLE", "Có thể sử dụng"],
            ["LOCKED", "Chưa đủ điều kiện"],
            ["REDEEMED", "Đã sử dụng"],
            ["EXPIRED", "Hết hạn"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            className={`min-h-11 shrink-0 rounded-lg px-4 text-sm ${tab === key ? "bg-[var(--theme-accent)] font-semibold text-[var(--theme-accent-contrast,#fff)]" : "text-[var(--theme-muted)]"}`}
            onClick={() => setTab(key)}
          >
            {label} (
            {vouchers.data?.filter(
              (voucher) => voucherTab(voucher, now) === key,
            ).length ?? 0}
            )
          </button>
        ))}
      </div>
      {vouchers.isPending && <p role="status">Đang tải voucher…</p>}
      {vouchers.isError && (
        <div role="alert">
          <p>Không thể tải voucher. Vui lòng thử lại.</p>
          <Button variant="outline" onClick={() => void vouchers.refetch()}>
            Thử lại
          </Button>
        </div>
      )}
      {vouchers.data?.length === 0 ? (
        <p className="rounded-xl border border-[var(--theme-border)] p-6">
          Bạn chưa nhận voucher nào.
        </p>
      ) : (
        !selected.length &&
        !vouchers.isPending && (
          <p className="py-8 text-center text-sm text-[var(--theme-muted)]">
            Chưa có voucher trong nhóm này.
          </p>
        )
      )}
      <ul className="grid gap-4 lg:grid-cols-2">
        {selected.map((voucher) => (
          <li key={voucher.id}>
            <VoucherCard voucher={voucher} />
          </li>
        ))}
      </ul>
    </section>
  );
}
