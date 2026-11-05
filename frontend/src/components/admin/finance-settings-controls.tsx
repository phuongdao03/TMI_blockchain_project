"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { adminFinanceApi } from "@/lib/api/client";
import type {
  FinanceSettingsUpdateInput,
  WalletWithdrawalSettings,
} from "@/lib/api/types";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

type FinanceForm = {
  minimum: string;
  maximum: string;
  dailyLimit: string;
  dailyCount: string;
  feeMode: WalletWithdrawalSettings["feeMode"];
  feeValue: string;
  twoPersonThreshold: string;
};

function settingsInput(
  form: FinanceForm,
  settings: WalletWithdrawalSettings,
  payoutLiveEnabled: boolean,
): FinanceSettingsUpdateInput | null {
  const values = [
    form.minimum,
    form.maximum,
    form.dailyLimit,
    form.dailyCount,
    form.feeValue,
  ];
  if (
    values.some((value) => !/^\d+$/.test(value)) ||
    (form.twoPersonThreshold !== "" && !/^\d+$/.test(form.twoPersonThreshold))
  )
    return null;
  const minimumAmountMinor = Number(form.minimum);
  const maximumAmountMinor = Number(form.maximum);
  const dailyLimitMinor = Number(form.dailyLimit);
  const dailyCountLimit = Number(form.dailyCount);
  const feeValue = Number(form.feeValue);
  const twoPersonThresholdMinor =
    form.twoPersonThreshold === "" ? null : Number(form.twoPersonThreshold);
  if (
    !Number.isSafeInteger(minimumAmountMinor) ||
    !Number.isSafeInteger(maximumAmountMinor) ||
    !Number.isSafeInteger(dailyLimitMinor) ||
    !Number.isSafeInteger(dailyCountLimit) ||
    !Number.isSafeInteger(feeValue) ||
    (twoPersonThresholdMinor !== null &&
      !Number.isSafeInteger(twoPersonThresholdMinor)) ||
    minimumAmountMinor <= 0 ||
    maximumAmountMinor < minimumAmountMinor ||
    (form.feeMode === "BPS" && feeValue > 10_000)
  )
    return null;
  return {
    withdrawalEnabled: settings.enabled,
    payoutLiveEnabled,
    minimumAmountMinor,
    maximumAmountMinor,
    dailyLimitMinor,
    dailyCountLimit,
    feeMode: form.feeMode,
    feeValue,
    twoPersonThresholdMinor,
  };
}

export function FinanceSettingsControls({
  settings,
}: {
  settings: WalletWithdrawalSettings;
}) {
  const client = useQueryClient();
  const [form, setForm] = useState<FinanceForm>(() => ({
    minimum: String(settings.minimumAmountMinor),
    maximum: String(settings.maximumAmountMinor),
    dailyLimit: String(settings.dailyLimitMinor),
    dailyCount: String(settings.dailyCountLimit),
    feeMode: settings.feeMode,
    feeValue: String(settings.feeValue),
    twoPersonThreshold:
      settings.twoPersonThresholdMinor === null
        ? ""
        : String(settings.twoPersonThresholdMinor),
  }));
  const [payoutLiveEnabled, setPayoutLiveEnabled] = useState(
    settings.payoutLiveEnabled,
  );
  const [confirmLive, setConfirmLive] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const update = useMutation({
    mutationFn: adminFinanceApi.updateSettings,
    onSuccess: async () => {
      setError(false);
      setMessage("Cấu hình đã được lưu.");
      setConfirmLive(false);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["admin", "withdrawal-settings"] }),
        client.invalidateQueries({ queryKey: ["wallet", "withdrawal-settings"] }),
      ]);
    },
    onError: () => {
      setMessage("");
      setError(true);
    },
  });

  const save = (live = payoutLiveEnabled) => {
    const input = settingsInput(form, settings, live);
    if (!input) {
      setError(true);
      setMessage("");
      return;
    }
    setError(false);
    setMessage("");
    update.mutate(input);
  };

  return (
    <div className="space-y-3">
      <form
        className="grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-2 lg:grid-cols-3"
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <h3 className="font-semibold sm:col-span-2 lg:col-span-3">
          Hạn mức rút và phí
        </h3>
        <NumberField label="Mức tối thiểu (đồng)" value={form.minimum} onChange={(minimum) => setForm({ ...form, minimum })} />
        <NumberField label="Mức tối đa (đồng)" value={form.maximum} onChange={(maximum) => setForm({ ...form, maximum })} />
        <NumberField label="Hạn mức mỗi ngày (đồng)" value={form.dailyLimit} onChange={(dailyLimit) => setForm({ ...form, dailyLimit })} />
        <NumberField label="Số yêu cầu mỗi ngày" value={form.dailyCount} onChange={(dailyCount) => setForm({ ...form, dailyCount })} />
        <label className="grid gap-1 text-sm font-semibold">
          Cách tính phí
          <select className={inputClass} onChange={(event) => setForm({ ...form, feeMode: event.target.value as FinanceForm["feeMode"] })} value={form.feeMode}>
            <option value="NONE">Không thu phí</option>
            <option value="FIXED">Mức cố định</option>
            <option value="BPS">Tỷ lệ tính theo phần vạn</option>
          </select>
        </label>
        <NumberField label={form.feeMode === "BPS" ? "Giá trị phần vạn" : form.feeMode === "FIXED" ? "Phí cố định (đồng)" : "Mức phí"} value={form.feeValue} onChange={(feeValue) => setForm({ ...form, feeValue })} />
        {form.feeMode === "BPS" ? <p className="text-xs text-[var(--theme-muted)]">Một phần vạn tương ứng với 0,01%.</p> : null}
        <NumberField label="Ngưỡng cần hai người duyệt (để trống nếu không áp dụng)" value={form.twoPersonThreshold} onChange={(twoPersonThreshold) => setForm({ ...form, twoPersonThreshold })} />
        <label className="flex min-h-11 items-center gap-2 text-sm font-semibold sm:col-span-2 lg:col-span-3">
          <input checked={settings.enabled} disabled type="checkbox" />
          Rút tiền được bật theo cấu hình hiệu lực
        </label>
        <Button className="min-h-11 sm:justify-self-start" disabled={update.isPending} type="submit">
          {update.isPending ? "Đang lưu…" : "Lưu hạn mức và phí"}
        </Button>
      </form>

      <div className="space-y-3 rounded-xl border border-amber-400 bg-amber-50 p-4 text-amber-950">
        <div>
          <h3 className="font-bold">Chi trả tự động</h3>
          <p className="mt-1 text-sm">
            Tính năng đang tắt theo mặc định. Chỉ bật khi môi trường, thông tin payOS và quy trình vận hành đã sẵn sàng.
          </p>
        </div>
        <label className="flex min-h-11 items-center gap-2 text-sm font-semibold">
          <input checked={payoutLiveEnabled} onChange={(event) => { setPayoutLiveEnabled(event.target.checked); setConfirmLive(false); }} type="checkbox" />
          Cho phép gửi lệnh chi trả tự động
        </label>
        {payoutLiveEnabled ? (
          <label className="flex items-start gap-2 text-sm">
            <input checked={confirmLive} onChange={(event) => setConfirmLive(event.target.checked)} type="checkbox" />
            <span>Tôi xác nhận đã kiểm tra môi trường, thông tin payOS và quy trình đối soát.</span>
          </label>
        ) : null}
        <Button
          className="min-h-11"
          disabled={update.isPending || (payoutLiveEnabled && !confirmLive)}
          onClick={() => save(payoutLiveEnabled)}
          type="button"
          variant="outline"
        >
          {update.isPending ? "Đang lưu…" : "Lưu trạng thái chi trả tự động"}
        </Button>
        <p className="text-xs">
          Trạng thái hiệu lực hiện tại: {settings.payoutLiveEnabled ? "đang bật" : "đang tắt"}.
        </p>
      </div>
      {message ? <p role="status" className="text-sm font-semibold text-emerald-800">{message}</p> : null}
      {error ? <p role="alert" className="text-sm text-red-700">Không lưu được thao tác tài chính. Hãy kiểm tra quyền, hạn mức và cấu hình môi trường.</p> : null}
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm font-semibold">
      {label}
      <input className={inputClass} inputMode="numeric" min="0" onChange={(event) => onChange(event.target.value)} required value={value} />
    </label>
  );
}
