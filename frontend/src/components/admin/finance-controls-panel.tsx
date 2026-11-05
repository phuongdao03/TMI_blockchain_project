"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { adminFinanceApi, withdrawalApi } from "@/lib/api/client";
import type { WalletWithdrawalSettings } from "@/lib/api/types";

import { FinanceSettingsControls } from "./finance-settings-controls";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

export function FinanceControlsPanel({
  settings,
  settingsLoading,
  settingsError,
  canRead,
  canManageSettings,
  canManageBanks,
  onRetrySettings,
}: {
  settings?: WalletWithdrawalSettings;
  settingsLoading: boolean;
  settingsError: boolean;
  canRead: boolean;
  canManageSettings: boolean;
  canManageBanks: boolean;
  onRetrySettings: () => void;
}) {
  const client = useQueryClient();
  const [bankBin, setBankBin] = useState("");
  const [bankName, setBankName] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [bankEnabled, setBankEnabled] = useState(true);
  const [savedMessage, setSavedMessage] = useState("");
  const [actionError, setActionError] = useState(false);
  const banks = useQuery({
    queryKey: ["wallet", "banks"],
    queryFn: withdrawalApi.banks,
    enabled: canRead || canManageBanks,
  });
  const reconciliation = useQuery({
    queryKey: ["admin", "finance", "reconciliation"],
    queryFn: adminFinanceApi.reconciliation,
    enabled: canRead,
  });
  const saveBank = useMutation({
    mutationFn: adminFinanceApi.saveBank,
    onSuccess: async () => {
      setActionError(false);
      setSavedMessage("Danh mục ngân hàng đã được cập nhật.");
      setBankBin("");
      setBankName("");
      setSourceReference("");
      await client.invalidateQueries({ queryKey: ["wallet", "banks"] });
    },
    onError: () => {
      setSavedMessage("");
      setActionError(true);
    },
  });

  return (
    <section aria-labelledby="finance-controls-title" className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
      <div>
        <h2 id="finance-controls-title" className="text-lg font-bold sm:text-xl">
          Cấu hình tài chính và đối soát
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Máy chủ luôn áp dụng hạn mức có hiệu lực cho yêu cầu rút và khoản chi trả.
        </p>
      </div>

      {canManageSettings ? (
        settingsLoading ? (
          <p aria-busy="true" className="text-sm" role="status">
            Đang tải cấu hình tài chính…
          </p>
        ) : settingsError || !settings ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4" role="alert">
            <p className="text-sm text-red-700">Chưa tải được cấu hình tài chính.</p>
            <Button className="min-h-10" onClick={onRetrySettings} type="button" variant="outline">Tải lại</Button>
          </div>
        ) : (
          <FinanceSettingsControls key={JSON.stringify(settings)} settings={settings} />
        )
      ) : null}

      {canManageBanks ? (
        <section aria-labelledby="bank-catalog-title" className="space-y-3">
          <h3 id="bank-catalog-title" className="font-bold">Ngân hàng được hỗ trợ</h3>
          {banks.isError ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4" role="alert">
              <p className="text-sm text-red-700">Chưa tải được danh mục ngân hàng.</p>
              <Button className="min-h-10" onClick={() => void banks.refetch()} type="button" variant="outline">Tải lại</Button>
            </div>
          ) : banks.data?.length ? (
            <ul className="flex flex-wrap gap-2">
              {banks.data.map((bank) => (
                <li className="rounded-full border border-[var(--theme-border)] px-3 py-1 text-sm" key={bank.bankBin}>
                  {bank.bankName} · Mã ngân hàng {bank.bankBin}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--theme-muted)]">
              Chưa có ngân hàng nào được bật hỗ trợ.
            </p>
          )}
          <form
            className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              saveBank.mutate({
                bankBin: bankBin.trim(),
                bankName: bankName.trim(),
                sourceReference: sourceReference.trim(),
                isEnabled: bankEnabled,
              });
            }}
          >
            <h4 className="font-semibold sm:col-span-2">Thêm hoặc cập nhật ngân hàng hỗ trợ</h4>
            <label className="grid gap-1 text-sm font-semibold">
              Mã định danh ngân hàng
              <input className={inputClass} inputMode="numeric" maxLength={12} minLength={5} onChange={(event) => setBankBin(event.target.value)} required value={bankBin} />
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Tên ngân hàng
              <input className={inputClass} maxLength={128} minLength={2} onChange={(event) => setBankName(event.target.value)} required value={bankName} />
            </label>
            <label className="grid gap-1 text-sm font-semibold sm:col-span-2">
              Đường dẫn nguồn xác thực
              <input className={inputClass} maxLength={512} minLength={10} onChange={(event) => setSourceReference(event.target.value)} required type="url" value={sourceReference} />
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm font-semibold sm:col-span-2">
              <input checked={bankEnabled} onChange={(event) => setBankEnabled(event.target.checked)} type="checkbox" />
              Cho phép chọn ngân hàng khi rút tiền
            </label>
            <Button className="min-h-11 sm:justify-self-start" disabled={saveBank.isPending} type="submit">
              {saveBank.isPending ? "Đang lưu…" : "Lưu ngân hàng"}
            </Button>
          </form>
        </section>
      ) : null}

      {canRead ? (
        <section aria-labelledby="finance-reconciliation-title" className="rounded-xl border border-[var(--theme-border)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 id="finance-reconciliation-title" className="font-bold">Đối soát sổ cái và khoản chi trả</h3>
            <Button className="min-h-10" disabled={reconciliation.isFetching} onClick={() => void reconciliation.refetch()} type="button" variant="outline">
              Làm mới
            </Button>
          </div>
          {reconciliation.isPending ? (
            <p aria-busy="true" className="mt-3 text-sm" role="status">Đang kiểm tra đối soát…</p>
          ) : reconciliation.isError ? (
            <p role="alert" className="mt-3 text-sm text-red-700">Chưa tải được dữ liệu đối soát.</p>
          ) : reconciliation.data ? (
            <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <p>Sổ đã kiểm tra: <strong>{reconciliation.data.checkedJournals}</strong></p>
              <p>Sổ chưa cân bằng: <strong>{reconciliation.data.unbalancedJournals}</strong></p>
              <p>Sai lệch số dư đang giữ: <strong>{reconciliation.data.reservedBalanceMismatches.length}</strong></p>
              <p>Khoản chi trả cần xử lý: <strong>{reconciliation.data.payoutExceptions.length}</strong></p>
            </div>
          ) : null}
        </section>
      ) : null}

      {savedMessage ? <p role="status" className="text-sm font-semibold text-emerald-800">{savedMessage}</p> : null}
      {actionError ? <p role="alert" className="text-sm text-red-700">Không thực hiện được thao tác tài chính. Hãy kiểm tra quyền và thông tin ngân hàng.</p> : null}
    </section>
  );
}
