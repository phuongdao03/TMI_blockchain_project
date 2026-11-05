"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { WalletBank, WalletBankAccount } from "@/lib/api/types";
import { withdrawalApi } from "@/lib/api/client";
import { bankVerificationStatusLabel } from "@/lib/wallet-presentation";

const inputClass =
  "min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base";

export function BankAccountsPanel({
  banks,
  accounts,
  isLoading,
  isError,
  onRetry,
}: {
  banks: WalletBank[];
  accounts: WalletBankAccount[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  const client = useQueryClient();
  const [bankBin, setBankBin] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountName, setAccountName] = useState("");
  const [formError, setFormError] = useState(false);
  const refresh = () =>
    client.invalidateQueries({ queryKey: ["wallet", "bank-accounts"] });
  const add = useMutation({
    mutationFn: () =>
      withdrawalApi.addBankAccount({
        bankBin,
        accountNumber: accountNumber.trim(),
        accountName: accountName.trim(),
        isDefault: accounts.filter((item) => item.isActive).length === 0,
      }),
    onSuccess: () => {
      setAccountNumber("");
      setAccountName("");
      setFormError(false);
      void refresh();
    },
    onError: () => setFormError(true),
  });
  const setDefault = useMutation({
    mutationFn: withdrawalApi.setDefaultBankAccount,
    onSuccess: refresh,
  });
  const disable = useMutation({
    mutationFn: withdrawalApi.disableBankAccount,
    onSuccess: refresh,
  });

  return (
    <section aria-labelledby="bank-accounts-title" className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
      <div>
        <h2 id="bank-accounts-title" className="text-lg font-bold sm:text-xl">
          Tài khoản ngân hàng
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Số tài khoản lưu trữ an toàn và chỉ hiển thị dạng che sau khi thêm.
        </p>
      </div>
      {isLoading ? (
        <p aria-busy="true" className="text-sm" role="status">
          Đang tải tài khoản ngân hàng…
        </p>
      ) : isError ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4" role="alert">
          <p className="text-sm text-red-700">Chưa tải được thông tin ngân hàng.</p>
          <Button className="min-h-10" onClick={onRetry} type="button" variant="outline">Tải lại</Button>
        </div>
      ) : accounts.length ? (
        <ul className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)] px-4">
          {accounts.map((account) => (
            <li
              className="flex flex-wrap items-center justify-between gap-3 py-3"
              key={account.id}
            >
              <div className="min-w-0">
                <p className="font-semibold">{account.bankName}</p>
                <p className="text-sm text-[var(--theme-muted)]">
                  {account.accountName} · {account.accountNumberMasked}
                </p>
                <p className="text-xs text-[var(--theme-muted)]">
                  Trạng thái xác minh: {bankVerificationStatusLabel(account.verificationStatus)}
                  {account.isDefault ? " · Mặc định" : ""}
                </p>
              </div>
              {account.isActive ? (
                <div className="flex flex-wrap gap-2">
                  {!account.isDefault ? (
                    <Button
                      className="min-h-10"
                      disabled={setDefault.isPending}
                      onClick={() => setDefault.mutate(account.id)}
                      type="button"
                      variant="outline"
                    >
                      Đặt mặc định
                    </Button>
                  ) : null}
      {setDefault.isError || disable.isError ? (
        <p role="alert" className="text-sm text-red-700">
          Không cập nhật được trạng thái tài khoản. Vui lòng tải lại và thử lại.
        </p>
      ) : null}
                  <Button
                    className="min-h-10"
                    disabled={disable.isPending}
                    onClick={() => disable.mutate(account.id)}
                    type="button"
                    variant="outline"
                  >
                    Vô hiệu hóa
                  </Button>
                </div>
              ) : (
                <span className="text-sm text-[var(--theme-muted)]">
                  Đã vô hiệu hóa
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
          Bạn chưa thêm tài khoản nhận tiền.
        </p>
      )}

      <form
        className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          const selected = banks.find((bank) => bank.bankBin === bankBin);
          if (selected && accountNumber.trim() && accountName.trim())
            add.mutate();
        }}
      >
        <h3 className="font-semibold sm:col-span-2">Thêm tài khoản</h3>
        <label className="grid gap-1 text-sm font-semibold sm:col-span-2">
          Ngân hàng
          <select
            className={inputClass}
            onChange={(event) => setBankBin(event.target.value)}
            required
            value={bankBin}
          >
            <option value="">Chọn ngân hàng</option>
            {banks.map((bank) => (
              <option key={bank.bankBin} value={bank.bankBin}>
                {bank.bankName}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Số tài khoản
          <input
            autoComplete="off"
            className={inputClass}
            inputMode="numeric"
            maxLength={32}
            minLength={6}
            onChange={(event) => setAccountNumber(event.target.value)}
            required
            value={accountNumber}
          />
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Tên chủ tài khoản
          <input
            autoComplete="off"
            className={inputClass}
            maxLength={120}
            minLength={2}
            onChange={(event) => setAccountName(event.target.value)}
            required
            value={accountName}
          />
        </label>
        <p className="text-xs text-[var(--theme-muted)] sm:col-span-2">
          Tên chủ tài khoản cần trùng với thông tin ngân hàng. Tài khoản mới
          có thể cần được xác minh trước khi quản trị viên duyệt yêu cầu rút.
        </p>
        {formError ? (
          <p role="alert" className="text-sm text-red-700 sm:col-span-2">
            Chưa thêm được tài khoản. Hãy kiểm tra thông tin hoặc thử lại.
          </p>
        ) : null}
        <Button
          className="min-h-11 sm:col-span-2 sm:justify-self-start"
          disabled={add.isPending || banks.length === 0}
          type="submit"
        >
          {add.isPending ? "Đang lưu…" : "Lưu tài khoản"}
        </Button>
      </form>
    </section>
  );
}
