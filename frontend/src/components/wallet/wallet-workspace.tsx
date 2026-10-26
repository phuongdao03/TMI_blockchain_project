"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Wallet } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { walletApi } from "@/lib/api/client";
import type { WalletSummary, WalletTopup } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { safeLocalDestination } from "@/lib/auth/safe-destination";

export const formatVnd = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
export const walletKey = (userId?: string) => ["wallet", userId] as const;

export function WalletWorkspace({
  returnTo,
  previewData,
}: {
  returnTo?: string;
  previewData?: WalletSummary;
}) {
  const user = useAuthUser();
  const client = useQueryClient();
  const queryKey = walletKey(user?.id);
  const wallet = useQuery({
    queryKey,
    queryFn: walletApi.summary,
    enabled: !previewData,
    initialData: previewData,
    staleTime: 0,
    refetchInterval: previewData ? false : 10_000,
  });
  const [amount, setAmount] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [activeTopup, setActiveTopup] = useState<WalletTopup | null>(null);
  const topup = useMutation({
    mutationFn: () => walletApi.topup(Number(amount), key),
    onSuccess: (result) => {
      setActiveTopup(result.status === "PAID" ? null : result);
      void client.invalidateQueries({ queryKey });
    },
  });
  const reconcile = useMutation({
    mutationFn: walletApi.reconcile,
    onSuccess: (result) => {
      if (result.status === "PAID" && activeTopup?.id === result.id) {
        setActiveTopup(null);
      }
      void client.invalidateQueries({ queryKey });
    },
  });
  const resume = useMutation({
    mutationFn: walletApi.resume,
    onSuccess: (result) => {
      setActiveTopup(result.status === "PAID" ? null : result);
      void client.invalidateQueries({ queryKey });
    },
  });
  if (wallet.isPending) return <p role="status">Đang tải ví của bạn…</p>;
  if (!wallet.data)
    return (
      <div role="alert">
        <p>Chưa thể tải ví. Vui lòng thử lại.</p>
        <Button onClick={() => void wallet.refetch()}>Thử lại</Button>
      </div>
    );
  const data = wallet.data;
  const validAmount =
    /^\d+$/.test(amount) &&
    Number(amount) >= 1000 &&
    Number(amount) <= 1_000_000_000;
  const isAdmin = user?.roles.includes("SUPER_ADMIN") ?? false;
  const activeTopupPaid = data.topups.some(
    (item) => item.id === activeTopup?.id && item.status === "PAID",
  );
  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-8">
      <header>
        <p className="text-sm text-[var(--theme-muted)]">
          Tài khoản Tinh Hoa Việt
        </p>
        <h1 className="mt-2 text-3xl font-bold">Ví của tôi</h1>
        <p className="mt-3 text-[var(--theme-muted)]">
          Nạp tiền và thanh toán các dịch vụ trong cộng đồng.
        </p>
      </header>
      {returnTo && (
        <Link
          className="inline-flex min-h-11 items-center font-semibold underline"
          href={safeLocalDestination(returnTo, "/workspace")}
        >
          Quay lại khoản cần thanh toán
        </Link>
      )}
      <section
        aria-label="Số dư ví"
        className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 sm:p-8"
      >
        <Wallet aria-hidden="true" className="size-6 text-primary-700" />
        <p className="mt-5 text-[var(--theme-muted)]">Số dư khả dụng</p>
        <p className="mt-2 break-all text-4xl font-bold">
          {formatVnd(data.balanceMinor)}
        </p>
        <p className="mt-4 text-sm text-[var(--theme-muted)]">
          Số dư trả trước nội bộ bằng VNĐ.
        </p>
      </section>
      {data.provider === "mock" && (
        <p
          role="status"
          className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"
        >
          Môi trường thử nghiệm — không chuyển tiền thật.
        </p>
      )}
      {previewData && (
        <p
          role="status"
          className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 text-sm"
        >
          Bản xem giao diện dùng số liệu minh họa; các thao tác giao dịch đã
          tắt.
        </p>
      )}
      {isAdmin ? (
        <section
          aria-label="Nạp tiền vào ví"
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-5"
        >
          <h2 className="text-xl font-bold">Ví quản trị</h2>
          <p className="mt-2 text-[var(--theme-muted)]">
            Tài khoản quản trị không thể tạo giao dịch nạp tiền vào ví.
          </p>
        </section>
      ) : (
        <section aria-labelledby="topup-title">
          <h2 id="topup-title" className="text-xl font-bold">
            Nạp tiền vào ví
          </h2>
          <form
            className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (validAmount && !topup.isPending && !previewData)
                topup.mutate();
            }}
          >
            <label
              className="flex-1 text-sm font-semibold"
              htmlFor="wallet-topup"
            >
              Số tiền (VNĐ)
              <input
                id="wallet-topup"
                disabled={Boolean(previewData) || topup.isPending}
                inputMode="numeric"
                pattern="[0-9]+"
                required
                autoComplete="off"
                className="mt-2 min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-base"
                value={amount}
                onChange={(event) => {
                  setAmount(event.target.value);
                  setKey(crypto.randomUUID());
                  topup.reset();
                }}
                aria-describedby="topup-help"
              />
            </label>
            <Button
              type="submit"
              disabled={Boolean(previewData) || !validAmount || topup.isPending}
            >
              {topup.isPending ? "Đang tạo giao dịch…" : "Nạp tiền"}
            </Button>
          </form>
          <p id="topup-help" className="mt-2 text-sm text-[var(--theme-muted)]">
            Nhập số nguyên từ 1.000đ đến 1.000.000.000đ. Số dư chỉ tăng sau khi
            thanh toán được xác minh.
          </p>
          {topup.isError && (
            <p role="alert" className="mt-3 text-red-700">
              Chưa thể tạo giao dịch. Thử lại sẽ tiếp tục cùng yêu cầu nạp tiền.
            </p>
          )}
        </section>
      )}
      {activeTopup && !activeTopupPaid && !isAdmin && (
        <section
          aria-labelledby="topup-payment-title"
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
          aria-live="polite"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-primary-800">
                Thanh toán an toàn trong trang
              </p>
              <h2 id="topup-payment-title" className="mt-1 text-xl font-bold">
                Quét mã để nạp {formatVnd(activeTopup.amountMinor)}
              </h2>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                Mã giao dịch {activeTopup.orderCode} · Hạn đến{" "}
                {new Date(activeTopup.expiresAt).toLocaleString("vi-VN")}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => setActiveTopup(null)}
              type="button"
            >
              Ẩn hướng dẫn
            </Button>
          </div>
          <div className="mt-6 grid gap-6 sm:grid-cols-[15rem_minmax(0,1fr)] sm:items-center">
            {activeTopup.qrPayload ? (
              <Image
                alt={`Mã QR thanh toán ${formatVnd(activeTopup.amountMinor)}`}
                className="mx-auto rounded-xl border border-[var(--theme-border)] bg-white p-2"
                height={240}
                src={`/api/v1/wallet/topups/${encodeURIComponent(activeTopup.id)}/qr`}
                unoptimized
                width={240}
              />
            ) : (
              <p className="rounded-xl bg-[var(--theme-elevated)] p-4 text-sm text-[var(--theme-muted)]">
                Mã QR chưa sẵn sàng. Vui lòng dùng thông tin chuyển khoản hoặc
                thử khôi phục giao dịch.
              </p>
            )}
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              {activeTopup.bankAccountName && (
                <div>
                  <dt className="text-[var(--theme-muted)]">Chủ tài khoản</dt>
                  <dd className="mt-1 font-semibold">
                    {activeTopup.bankAccountName}
                  </dd>
                </div>
              )}
              {activeTopup.bankBin && (
                <div>
                  <dt className="text-[var(--theme-muted)]">Mã ngân hàng</dt>
                  <dd className="mt-1 font-semibold">{activeTopup.bankBin}</dd>
                </div>
              )}
              {activeTopup.bankAccountNumber && (
                <div>
                  <dt className="text-[var(--theme-muted)]">Số tài khoản</dt>
                  <dd className="mt-1 font-semibold">
                    {activeTopup.bankAccountNumber}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-[var(--theme-muted)]">Số tiền chuyển</dt>
                <dd className="mt-1 font-semibold">
                  {formatVnd(activeTopup.amountMinor)}
                </dd>
              </div>
              {activeTopup.transferDescription && (
                <div className="sm:col-span-2">
                  <dt className="text-[var(--theme-muted)]">
                    Nội dung chuyển khoản
                  </dt>
                  <dd className="mt-1 break-all rounded-lg bg-[var(--theme-elevated)] p-3 font-mono font-semibold">
                    {activeTopup.transferDescription}
                  </dd>
                </div>
              )}
              <div className="sm:col-span-2">
                <dt className="text-[var(--theme-muted)]">Trạng thái</dt>
                <dd className="mt-1 font-semibold">
                  Đang chờ xác minh. Số dư ví chỉ tăng sau khi nhận được xác
                  nhận thanh toán.
                </dd>
              </div>
            </dl>
          </div>
        </section>
      )}
      <section aria-labelledby="pending-title">
        <h2 id="pending-title" className="text-xl font-bold">
          Các lần nạp gần đây
        </h2>
        {data.topups.length === 0 ? (
          <p className="mt-3 text-[var(--theme-muted)]">
            Bạn chưa có giao dịch nạp tiền.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-[var(--theme-border)]">
            {data.topups.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-3 py-4"
              >
                <div>
                  <p className="font-semibold">{formatVnd(item.amountMinor)}</p>
                  <p className="mt-1 text-sm text-[var(--theme-muted)]">
                    {item.status === "PAID"
                      ? "Đã nạp thành công"
                      : item.status === "FAILED"
                        ? "Nạp tiền thất bại"
                        : item.status === "CANCELLED"
                          ? "Đã hủy"
                          : item.status === "EXPIRED"
                            ? "Đã hết hạn"
                            : "Chờ xác minh thanh toán"}{" "}
                    · {item.orderCode}
                  </p>
                </div>
                {item.status !== "PAID" && (
                  <div className="flex flex-wrap gap-2">
                    {["PENDING", "PROCESSING"].includes(item.status) && (
                      <Button
                        variant="outline"
                        disabled={Boolean(previewData) || resume.isPending}
                        onClick={() => resume.mutate(item.id)}
                      >
                        {resume.isPending && resume.variables === item.id
                          ? "Đang tải…"
                          : "Hiện mã QR"}
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      disabled={Boolean(previewData) || reconcile.isPending}
                      onClick={() => reconcile.mutate(item.id)}
                    >
                      <RefreshCw aria-hidden="true" className="size-4" /> Kiểm
                      tra
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {reconcile.isError && (
          <p role="alert" className="text-red-700">
            Chưa thể kiểm tra kết quả. Tiền chưa xác minh sẽ không được cộng vào
            ví.
          </p>
        )}
        {resume.isError && (
          <p role="alert" className="text-red-700">
            Chưa thể khôi phục giao dịch. Yêu cầu nạp vẫn được giữ lại.
          </p>
        )}
      </section>
      <section aria-labelledby="transactions-title">
        <h2 id="transactions-title" className="text-xl font-bold">
          Lịch sử thu chi
        </h2>
        {data.transactions.length === 0 ? (
          <p className="mt-3 text-[var(--theme-muted)]">
            Các khoản thu chi sẽ xuất hiện tại đây.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-[var(--theme-border)]">
            {data.transactions.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-4 py-4"
              >
                <div className="min-w-0">
                  <p className="break-words font-medium">{item.description}</p>
                  <p className="mt-1 text-sm text-[var(--theme-muted)]">
                    {new Date(item.createdAt).toLocaleString("vi-VN")} · Số dư{" "}
                    {formatVnd(item.balanceAfter)}
                  </p>
                </div>
                <p className="shrink-0 font-bold">
                  {item.walletDelta > 0 ? "+" : ""}
                  {formatVnd(item.walletDelta)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
