"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { affiliateApi, withdrawalApi } from "@/lib/api/client";
import type { WalletWithdrawal } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { withdrawalStatusLabel } from "@/lib/wallet-presentation";
import { formatVnd } from "@/lib/wallet/summary";

import { BankAccountsPanel } from "./bank-accounts-panel";

function requestKey() {
  return globalThis.crypto?.randomUUID?.() ?? `withdrawal-${Date.now()}`;
}

function WithdrawalRow({
  item,
  onCancel,
  isCancelling,
}: {
  item: WalletWithdrawal;
  onCancel: (id: string) => void;
  isCancelling: boolean;
}) {
  return (
    <li className="py-4 first:pt-1 last:pb-1">
      <article className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="font-semibold">{formatVnd(item.amountMinor)}</p>
          <p className="text-sm text-[var(--theme-muted)]">
            {item.bankNameSnapshot} · {item.accountNumberMasked}
          </p>
          <p className="text-xs text-[var(--theme-muted)]">
            {new Date(item.createdAt).toLocaleString("vi-VN")}
          </p>
          {item.rejectionReason ? (
            <p className="text-sm text-red-700">
              Lý do: {item.rejectionReason}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex min-h-9 items-center rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 text-xs font-bold">
            {withdrawalStatusLabel(item.status)}
          </span>
          {item.status === "PENDING_REVIEW" ? (
            <Button
              className="min-h-10"
              disabled={isCancelling}
              onClick={() => onCancel(item.id)}
              type="button"
              variant="outline"
            >
              Hủy yêu cầu
            </Button>
          ) : null}
        </div>
      </article>
      <p className="mt-2 text-xs text-[var(--theme-muted)]">
        Phí {formatVnd(item.feeMinor)} · dự kiến nhận{" "}
        {formatVnd(item.netAmountMinor)}
      </p>
    </li>
  );
}

export function WalletWithdrawalWorkspace() {
  const user = useAuthUser();
  const client = useQueryClient();
  const privileged = user?.roles.some((role) =>
    ["SUPER_ADMIN", "MODERATOR"].includes(role),
  );
  const userId = user?.id;
  const affiliate = useQuery({
    queryKey: ["affiliate", "me", userId],
    queryFn: affiliateApi.me,
    enabled: Boolean(userId) && !privileged,
    staleTime: 0,
  });
  const banks = useQuery({
    queryKey: ["wallet", "banks"],
    queryFn: withdrawalApi.banks,
    enabled: Boolean(userId) && !privileged,
  });
  const accounts = useQuery({
    queryKey: ["wallet", "bank-accounts", userId],
    queryFn: withdrawalApi.bankAccounts,
    enabled: Boolean(userId) && !privileged,
  });
  const settings = useQuery({
    queryKey: ["wallet", "withdrawal-settings"],
    queryFn: withdrawalApi.settings,
    enabled: Boolean(userId) && !privileged,
  });
  const withdrawals = useQuery({
    queryKey: ["wallet", "withdrawals", userId],
    queryFn: withdrawalApi.list,
    enabled: Boolean(userId) && !privileged,
  });
  const [amount, setAmount] = useState("");
  const [bankAccountId, setBankAccountId] = useState("");
  const [requestError, setRequestError] = useState(false);
  const key = useRef(requestKey());
  const enabledAccounts = (accounts.data ?? []).filter((item) => item.isActive);
  const selectedAccountId =
    bankAccountId || enabledAccounts.find((item) => item.isDefault)?.id || "";
  const available = affiliate.data?.availableBalanceMinor ?? 0;
  const min = settings.data?.minimumAmountMinor ?? 0;
  const max = settings.data?.maximumAmountMinor ?? 0;
  const amountMinor = /^\d+$/.test(amount) ? Number(amount) : 0;
  const validAmount =
    Number.isSafeInteger(amountMinor) &&
    amountMinor >= min &&
    amountMinor <= max &&
    amountMinor <= available;
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["wallet", "withdrawals", userId] }),
      client.invalidateQueries({ queryKey: ["affiliate", "me", userId] }),
    ]);
  };
  const create = useMutation({
    mutationFn: () =>
      withdrawalApi.create(selectedAccountId, amountMinor, key.current),
    onSuccess: async () => {
      setAmount("");
      setRequestError(false);
      key.current = requestKey();
      await refresh();
    },
    onError: () => setRequestError(true),
  });
  const cancel = useMutation({
    mutationFn: withdrawalApi.cancel,
    onSuccess: refresh,
  });

  if (privileged) return null;

  const loading = affiliate.isPending || settings.isPending;
  const unavailable = settings.data && !settings.data.enabled;
  return (
    <div className="space-y-5">
      <section aria-labelledby="commission-withdrawable-title">
        <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6">
          <h2 id="commission-withdrawable-title" className="text-xl font-bold">
            Hoa hồng có thể rút
          </h2>
          {affiliate.isPending ? (
            <p aria-busy="true" className="mt-3 text-sm" role="status">
              Đang tải số dư hoa hồng…
            </p>
          ) : affiliate.isError ? (
            <p role="alert" className="mt-3 text-sm text-red-700">
              Chưa tải được số dư hoa hồng.
            </p>
          ) : (
            <p className="mt-2 break-words text-3xl font-bold">
              {formatVnd(available)}
            </p>
          )}
          <p className="mt-2 text-sm text-[var(--theme-muted)]">
            Bạn chỉ có thể rút hoa hồng đang khả dụng. Số dư nạp để thanh toán
            dịch vụ không thể rút.
          </p>
        </div>
      </section>

      <BankAccountsPanel
        accounts={accounts.data ?? []}
        banks={banks.data ?? []}
        isError={accounts.isError || banks.isError}
        isLoading={accounts.isPending || banks.isPending}
        onRetry={() => void Promise.all([accounts.refetch(), banks.refetch()])}
      />

      <section
        aria-labelledby="withdrawal-request-title"
        className="space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
      >
        <div>
          <h2 id="withdrawal-request-title" className="text-xl font-bold">
            Yêu cầu rút hoa hồng
          </h2>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            Yêu cầu sẽ chờ quản trị viên kiểm tra. Gửi yêu cầu không tự động
            chuyển tiền.
          </p>
        </div>
        {loading ? (
          <p aria-busy="true" className="text-sm" role="status">
            Đang tải điều kiện rút…
          </p>
        ) : settings.isError || affiliate.isError ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
            role="alert"
          >
            <p className="text-sm text-red-700">
              Chưa tải được điều kiện rút. Vui lòng thử lại.
            </p>
            <Button
              className="min-h-10"
              onClick={() =>
                void Promise.all([settings.refetch(), affiliate.refetch()])
              }
              type="button"
              variant="outline"
            >
              Tải lại
            </Button>
          </div>
        ) : unavailable ? (
          <p
            className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
            role="status"
          >
            Chức năng rút tiền hiện chưa được mở. Bạn vẫn có thể xem lịch sử yêu
            cầu rút.
          </p>
        ) : (
          <form
            className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end"
            onSubmit={(event) => {
              event.preventDefault();
              if (selectedAccountId && validAmount && !create.isPending)
                create.mutate();
            }}
          >
            <label className="grid gap-1 text-sm font-semibold">
              Tài khoản nhận tiền
              <select
                className="min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base"
                disabled={enabledAccounts.length === 0}
                onChange={(event) => {
                  setBankAccountId(event.target.value);
                  key.current = requestKey();
                }}
                required
                value={selectedAccountId}
              >
                <option value="">Chọn tài khoản</option>
                {enabledAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.bankName} · {account.accountNumberMasked}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Số tiền muốn rút (đồng)
              <input
                className="min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base"
                disabled={unavailable || create.isPending}
                inputMode="numeric"
                min={min}
                onChange={(event) => {
                  setAmount(event.target.value);
                  key.current = requestKey();
                  setRequestError(false);
                }}
                pattern="[0-9]+"
                required
                value={amount}
              />
            </label>
            <Button
              className="min-h-12"
              disabled={
                !selectedAccountId ||
                !validAmount ||
                create.isPending ||
                available <= 0
              }
              type="submit"
            >
              {create.isPending ? "Đang gửi…" : "Gửi yêu cầu rút"}
            </Button>
            <p className="text-xs text-[var(--theme-muted)] sm:col-span-3">
              Mức rút {formatVnd(min)}–{formatVnd(max)}. Bạn cần xác minh danh
              tính và dùng tài khoản ngân hàng đủ điều kiện.
            </p>
            {requestError ? (
              <p role="alert" className="text-sm text-red-700 sm:col-span-3">
                Chưa gửi được yêu cầu. Kiểm tra trạng thái trong lịch sử trước
                khi gửi lại.
              </p>
            ) : null}
          </form>
        )}
      </section>

      <section
        aria-labelledby="withdrawal-history-title"
        className="space-y-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
      >
        <h2
          id="withdrawal-history-title"
          className="text-lg font-bold sm:text-xl"
        >
          Lịch sử yêu cầu rút
        </h2>
        {create.data ? (
          <p
            role="status"
            className="mt-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-950"
          >
            Mã yêu cầu {create.data.providerReference}:{" "}
            {withdrawalStatusLabel(create.data.status)}. Gửi yêu cầu không tự
            động chuyển tiền.
          </p>
        ) : null}
        {withdrawals.isPending ? (
          <p aria-busy="true" className="py-5 text-sm" role="status">
            Đang tải lịch sử…
          </p>
        ) : withdrawals.isError ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
            role="alert"
          >
            <p className="text-sm text-red-700">
              Chưa tải được lịch sử yêu cầu rút.
            </p>
            <Button
              className="min-h-10"
              onClick={() => void withdrawals.refetch()}
              type="button"
              variant="outline"
            >
              Tải lại
            </Button>
          </div>
        ) : withdrawals.data?.length ? (
          <ul className="mt-2 divide-y divide-[var(--theme-border)]">
            {withdrawals.data.map((item) => (
              <WithdrawalRow
                isCancelling={cancel.isPending}
                item={item}
                key={item.id}
                onCancel={(id) => cancel.mutate(id)}
              />
            ))}
          </ul>
        ) : (
          <p className="mt-3 rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
            Chưa có yêu cầu rút nào.
          </p>
        )}
        {cancel.isError ? (
          <p role="alert" className="text-sm text-red-700">
            Không hủy được yêu cầu. Vui lòng tải lại trạng thái rồi thử lại.
          </p>
        ) : null}
      </section>
    </div>
  );
}
