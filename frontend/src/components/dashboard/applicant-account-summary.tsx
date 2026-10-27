"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { notificationApi, walletApi } from "@/lib/api/client";
import { formatVnd, walletKey } from "@/lib/wallet/summary";

export function ApplicantAccountSummary({ userId }: { userId: string }) {
  const wallet = useQuery({
    queryKey: walletKey(userId),
    queryFn: () => walletApi.summary(),
    staleTime: 30_000,
  });
  const unread = useQuery({
    queryKey: ["notifications", "unread-count", userId],
    queryFn: () => notificationApi.unreadCount(),
    staleTime: 30_000,
    refetchInterval: 45_000,
  });
  return (
    <section
      aria-label="Ví và thông báo"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
    >
      <div className="min-w-0 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
        <h2 className="text-sm font-bold text-[var(--theme-muted)]">
          Số dư khả dụng
        </h2>
        {wallet.isError ? (
          <div role="alert" className="mt-2 text-sm">
            <p>Chưa tải được số dư.</p>
            <button
              type="button"
              className="min-h-11 font-bold underline"
              onClick={() => void wallet.refetch()}
            >
              Tải lại số dư
            </button>
          </div>
        ) : wallet.data ? (
          <p className="mt-2 break-words text-2xl font-bold tabular-nums">
            {formatVnd(wallet.data.balanceMinor)}
          </p>
        ) : (
          <p role="status" className="mt-2 text-sm">
            Đang tải số dư…
          </p>
        )}
        <Link
          href="/wallet"
          className="mt-2 inline-flex min-h-11 items-center text-sm font-bold underline"
        >
          Mở ví và nạp tiền
        </Link>
      </div>
      <div className="min-w-0 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
        <h2 className="text-sm font-bold text-[var(--theme-muted)]">
          Thông báo của bạn
        </h2>
        {unread.isError ? (
          <div role="alert" className="mt-2 text-sm">
            <p>Chưa tải được thông báo.</p>
            <button
              type="button"
              className="min-h-11 font-bold underline"
              onClick={() => void unread.refetch()}
            >
              Tải lại số thông báo
            </button>
          </div>
        ) : unread.data ? (
          <p className="mt-2 text-lg font-bold">
            {unread.data.unreadCount > 0
              ? `${unread.data.unreadCount} thông báo chưa đọc`
              : "Không có thông báo chưa đọc"}
          </p>
        ) : (
          <p role="status" className="mt-2 text-sm">
            Đang tải thông báo…
          </p>
        )}
        <Link
          href="/notifications"
          className="mt-2 inline-flex min-h-11 items-center text-sm font-bold underline"
        >
          Xem thông báo
        </Link>
      </div>
    </section>
  );
}
