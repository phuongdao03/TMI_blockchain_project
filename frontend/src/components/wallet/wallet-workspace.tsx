"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Wallet } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { walletApi } from "@/lib/api/client";
import type { WalletSummary, WalletTopup } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { safeLocalDestination } from "@/lib/auth/safe-destination";
import { WalletWithdrawalWorkspace } from "@/components/wallet/wallet-withdrawal-workspace";

import { formatVnd, walletKey } from "@/lib/wallet/summary";
export { formatVnd, walletKey } from "@/lib/wallet/summary";

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
  const amountInputRef = useRef<HTMLInputElement>(null);
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [activeTopup, setActiveTopup] = useState<WalletTopup | null>(null);
  const [qrImageFailed, setQrImageFailed] = useState(false);
  const resume = useMutation({
    mutationFn: walletApi.resume,
    onSuccess: (result) => {
      setQrImageFailed(false);
      setActiveTopup(result.status === "PAID" ? null : result);
      void client.invalidateQueries({ queryKey });
    },
  });
  const topup = useMutation({
    mutationFn: () => walletApi.topup(Number(amount), key),
    onSuccess: (result) => {
      setQrImageFailed(false);
      setActiveTopup(result.status === "PAID" ? null : result);
      void client.invalidateQueries({ queryKey });
      if (result.status !== "PAID" && !result.qrPayload) {
        resume.mutate(result.id);
      }
    },
  });
  const reconcile = useMutation({
    mutationFn: walletApi.reconcile,
    onSuccess: (result) => {
      if (activeTopup?.id === result.id) {
        setActiveTopup(result.status === "PAID" ? null : result);
      }
      void client.invalidateQueries({ queryKey });
    },
  });
  const header = (
    <header>
      <p className="text-sm text-[var(--theme-muted)]">
        Tài khoản Tinh Hoa Việt
      </p>
      <h1 className="mt-2 text-3xl font-bold">Ví của tôi</h1>
      <p className="mt-3 text-[var(--theme-muted)]">
        Nạp tiền và thanh toán các dịch vụ trong cộng đồng.
      </p>
    </header>
  );
  if (wallet.isPending)
    return (
      <div className="mx-auto max-w-4xl space-y-8 pb-8">
        {header}
        <p
          aria-busy="true"
          className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 text-sm"
          role="status"
        >
          Đang tải số dư và lịch sử nạp ví…
        </p>
        {!previewData ? <WalletWithdrawalWorkspace /> : null}
      </div>
    );
  if (!wallet.data)
    return (
      <div className="mx-auto max-w-4xl space-y-5 pb-8">
        {header}
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
          role="alert"
        >
          <p className="text-sm text-red-700">
            Chưa tải được số dư trả trước và lịch sử nạp ví.
          </p>
          <Button
            className="min-h-10"
            onClick={() => void wallet.refetch()}
            type="button"
            variant="outline"
          >
            Tải lại ví
          </Button>
        </div>
        {!previewData ? <WalletWithdrawalWorkspace /> : null}
      </div>
    );
  const data = wallet.data;
  const amountValue = Number(amount);
  const validAmount =
    /^\d+$/.test(amount) &&
    Number.isSafeInteger(amountValue) &&
    amountValue >= 5_000;
  const isAdmin = user?.roles.includes("SUPER_ADMIN") ?? false;
  const currentTopup = activeTopup
    ? (data.topups.find((item) => item.id === activeTopup.id) ?? activeTopup)
    : null;
  const activeTopupPaid = currentTopup?.status === "PAID";
  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-8">
      {header}
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
          Số dư ví dùng để thanh toán dịch vụ trên nền tảng.
        </p>
      </section>
      {!previewData ? <WalletWithdrawalWorkspace /> : null}
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
              Số tiền cần nạp
              <span className="relative mt-2 block">
                <input
                  ref={amountInputRef}
                  id="wallet-topup"
                  disabled={Boolean(previewData) || topup.isPending}
                  inputMode="numeric"
                  required
                  autoComplete="off"
                  aria-describedby="topup-help"
                  className="min-h-14 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] py-3 pr-16 pl-4 text-xl font-semibold tabular-nums tracking-[0.02em] outline-none transition focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/25 disabled:opacity-60"
                  type="text"
                  value={formatAmountDigits(amount)}
                  onChange={(event) => {
                    const input = event.currentTarget;
                    const digitCountBeforeCaret = input.value
                      .slice(0, input.selectionStart ?? input.value.length)
                      .replace(/\D/g, "").length;
                    const nextAmount = input.value
                      .replace(/\D/g, "")
                      .replace(/^0+(?=\d)/, "");
                    setAmount(nextAmount);
                    setKey(crypto.randomUUID());
                    topup.reset();
                    window.requestAnimationFrame(() => {
                      if (document.activeElement !== input) return;
                      const position = caretAfterDigitCount(
                        formatAmountDigits(nextAmount),
                        digitCountBeforeCaret,
                      );
                      input.setSelectionRange(position, position);
                    });
                  }}
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-sm font-medium text-[var(--theme-muted)]">
                  đồng
                </span>
              </span>
            </label>
            <Button
              type="submit"
              disabled={Boolean(previewData) || !validAmount || topup.isPending}
            >
              {topup.isPending ? "Đang tạo giao dịch…" : "Nạp tiền"}
            </Button>
          </form>
          <p id="topup-help" className="mt-2 text-sm text-[var(--theme-muted)]">
            Nạp tối thiểu 5.000đ. Số dư ví tăng sau khi thanh toán được xác
            nhận.
          </p>
          {amount && !Number.isSafeInteger(amountValue) ? (
            <p className="mt-2 text-sm text-red-700" role="alert">
              Số tiền vượt quá giới hạn xử lý an toàn. Vui lòng nhập số tiền nhỏ
              hơn.
            </p>
          ) : null}
          {topup.isError && (
            <p role="alert" className="mt-3 text-red-700">
              Chưa thể tạo giao dịch. Thử lại sẽ tiếp tục cùng yêu cầu nạp tiền.
            </p>
          )}
        </section>
      )}
      {currentTopup && !activeTopupPaid && !isAdmin && (
        <section
          aria-labelledby="topup-payment-title"
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
          aria-live="polite"
        >
          {["FAILED", "CANCELLED", "EXPIRED"].includes(currentTopup.status) ? (
            <div className="space-y-3">
              <h2 id="topup-payment-title" className="text-xl font-bold">
                {currentTopup.status === "EXPIRED"
                  ? "Yêu cầu nạp tiền đã hết hạn"
                  : currentTopup.status === "CANCELLED"
                    ? "Yêu cầu nạp tiền đã bị hủy"
                    : "Nạp tiền chưa thành công"}
              </h2>
              <p className="text-sm text-[var(--theme-muted)]">
                {currentTopup.status === "EXPIRED"
                  ? "Yêu cầu có hiệu lực trong 10 phút. Nếu chưa chuyển tiền, bạn có thể tạo yêu cầu mới. Nếu đã chuyển, đừng thanh toán lần nữa; hãy kiểm tra trạng thái hoặc liên hệ hỗ trợ."
                  : "Nếu chưa chuyển tiền, bạn có thể tạo yêu cầu mới. Nếu đã chuyển, đừng thanh toán lần nữa; hãy kiểm tra trạng thái hoặc liên hệ hỗ trợ."}
              </p>
              <Button
                className="min-h-11"
                onClick={() => {
                  setActiveTopup(null);
                  setKey(crypto.randomUUID());
                }}
                type="button"
              >
                Tạo yêu cầu mới
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-primary-800">
                    Thanh toán qua mã QR
                  </p>
                  <h2
                    id="topup-payment-title"
                    className="mt-1 text-xl font-bold"
                  >
                    Quét mã để nạp {formatVnd(currentTopup.amountMinor)}
                  </h2>
                  <p className="mt-1 text-sm text-[var(--theme-muted)]">
                    Mã yêu cầu nạp {currentTopup.orderCode} · Hết hạn lúc{" "}
                    {new Date(currentTopup.expiresAt).toLocaleString("vi-VN")}
                  </p>
                  <p className="mt-2 text-sm text-[var(--theme-muted)]">
                    Yêu cầu có hiệu lực trong 10 phút. Quét mã bằng ứng dụng
                    ngân hàng và chuyển đúng số tiền cùng nội dung bên dưới.
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
                {currentTopup.qrPayload && !qrImageFailed ? (
                  <Image
                    alt={`Mã QR thanh toán ${formatVnd(currentTopup.amountMinor)}`}
                    className="mx-auto h-auto w-full max-w-60 rounded-xl border border-[var(--theme-border)] bg-white p-2"
                    height={240}
                    onError={() => setQrImageFailed(true)}
                    src={`/api/v1/wallet/topups/${encodeURIComponent(currentTopup.id)}/qr`}
                    unoptimized
                    width={240}
                  />
                ) : (
                  <div className="grid justify-items-center gap-3 rounded-xl bg-[var(--theme-elevated)] p-4 text-center">
                    <p className="text-sm text-[var(--theme-muted)]">
                      Chưa hiển thị được mã QR. Hãy khôi phục mã cho yêu cầu
                      này; không cần tạo yêu cầu mới.
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={resume.isPending}
                      onClick={() => resume.mutate(currentTopup.id)}
                    >
                      {resume.isPending
                        ? "Đang khôi phục mã…"
                        : "Khôi phục mã QR"}
                    </Button>
                  </div>
                )}
                {(resume.isError || qrImageFailed) &&
                  (!currentTopup.qrPayload || qrImageFailed) && (
                    <p className="mt-3 text-sm text-red-700" role="alert">
                      Chưa khôi phục được mã. Hãy thử lại hoặc dùng thông tin
                      chuyển khoản hiển thị trên trang này.
                    </p>
                  )}
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  {currentTopup.bankAccountName && (
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Chủ tài khoản
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {currentTopup.bankAccountName}
                      </dd>
                    </div>
                  )}
                  {currentTopup.bankBin && (
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Mã ngân hàng
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {currentTopup.bankBin}
                      </dd>
                    </div>
                  )}
                  {currentTopup.bankAccountNumber && (
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Số tài khoản
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {currentTopup.bankAccountNumber}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-[var(--theme-muted)]">
                      Số tiền chuyển
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {formatVnd(currentTopup.amountMinor)}
                    </dd>
                  </div>
                  {currentTopup.transferDescription && (
                    <div className="sm:col-span-2">
                      <dt className="text-[var(--theme-muted)]">
                        Nội dung chuyển khoản
                      </dt>
                      <dd className="mt-1 break-all rounded-lg bg-[var(--theme-elevated)] p-3 font-mono font-semibold">
                        {currentTopup.transferDescription}
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
            </>
          )}
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
                {["PENDING", "PROCESSING"].includes(item.status) && (
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

function formatAmountDigits(digits: string) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function caretAfterDigitCount(value: string, digitCount: number) {
  if (digitCount <= 0) return 0;
  let seen = 0;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (character && /\d/.test(character)) seen += 1;
    if (seen === digitCount) {
      return value[index + 1] === "." ? index + 2 : index + 1;
    }
  }
  return value.length;
}
