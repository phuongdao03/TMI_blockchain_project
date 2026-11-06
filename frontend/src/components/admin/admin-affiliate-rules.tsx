"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { adminAffiliateApi } from "@/lib/api/client";
import {
  affiliateServiceLabel,
  basisPointsAsPercent,
  ruleStatusLabel,
} from "@/lib/affiliate-presentation";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

const services = [
  { code: "DOSSIER_SUBMISSION", label: "Nộp hồ sơ" },
  { code: "MEMBERSHIP", label: "Gói thành viên" },
  { code: "ADVERTISING", label: "Dịch vụ quảng cáo" },
] as const;

type RateDraft = { id: number; serviceCode: string; percent: string };

function percentToBasisPoints(value: string) {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d{1,3}(?:\.\d{1,2})?$/.test(normalized)) return null;
  const [whole = "0", fraction = ""] = normalized.split(".");
  const basisPoints = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return basisPoints <= 10_000 ? basisPoints : null;
}

export function AdminAffiliateRules() {
  const client = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [attributionWindowDays, setAttributionWindowDays] = useState("30");
  const [holdDays, setHoldDays] = useState("30");
  const [rates, setRates] = useState<RateDraft[]>([
    { id: 0, serviceCode: "", percent: "" },
  ]);
  const nextRateId = useRef(1);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const rules = useQuery({
    queryKey: ["admin", "affiliate", "rules"],
    queryFn: adminAffiliateApi.commissionRules,
  });
  const create = useMutation({
    mutationFn: adminAffiliateApi.createCommissionRules,
    onSuccess: async () => {
      setError("");
      setMessage("Đã tạo bản nháp quy tắc hoa hồng.");
      setRates([{ id: nextRateId.current++, serviceCode: "", percent: "" }]);
      await client.invalidateQueries({
        queryKey: ["admin", "affiliate", "rules"],
      });
    },
    onError: () =>
      setError(
        "Không tạo được bản nháp. Hãy kiểm tra thông tin và quyền quản lý.",
      ),
  });
  const publish = useMutation({
    mutationFn: adminAffiliateApi.publishCommissionRules,
    onSuccess: async () => {
      setError("");
      setMessage("Đã phát hành phiên bản quy tắc.");
      await client.invalidateQueries({
        queryKey: ["admin", "affiliate", "rules"],
      });
    },
    onError: () =>
      setError(
        "Không phát hành được quy tắc. Phiên bản có thể đã được cập nhật trước đó.",
      ),
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const rateEntries = rates.map((rate) => ({
      serviceCode: rate.serviceCode,
      directRateBasisPoints: percentToBasisPoints(rate.percent),
    }));
    const selectedCodes = rateEntries.map((rate) => rate.serviceCode);
    const validRates =
      rateEntries.length > 0 &&
      rateEntries.every(
        (rate) => rate.serviceCode && rate.directRateBasisPoints !== null,
      ) &&
      new Set(selectedCodes).size === selectedCodes.length;
    const attributionDays = Number(attributionWindowDays);
    const holdDaysValue = Number(holdDays);
    if (
      !validRates ||
      !Number.isInteger(attributionDays) ||
      attributionDays < 0 ||
      attributionDays > 3650 ||
      !Number.isInteger(holdDaysValue) ||
      holdDaysValue < 0 ||
      holdDaysValue > 3650
    ) {
      setMessage("");
      setError(
        "Hãy kiểm tra thời hạn và tỷ lệ hoa hồng. Mỗi dịch vụ cần có tỷ lệ từ 0 đến 100% và không được lặp lại.",
      );
      return;
    }
    setError("");
    setMessage("");
    const commissionRates = rateEntries.map((rate) => ({
      serviceCode: rate.serviceCode,
      directRateBasisPoints: rate.directRateBasisPoints!,
    }));
    create.mutate({
      enabled,
      attributionWindowDays: attributionDays,
      holdDays: holdDaysValue,
      rates: commissionRates,
    });
  };

  return (
    <section
      aria-labelledby="affiliate-rules-title"
      className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
    >
      <div>
        <h2 id="affiliate-rules-title" className="text-lg font-bold sm:text-xl">
          Quy tắc hoa hồng
        </h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Tạo bản nháp, kiểm tra thông tin rồi phát hành khi đã sẵn sàng.
        </p>
      </div>
      <form
        className="grid gap-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:p-5"
        onSubmit={submit}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-sm font-semibold">
            Thời hạn ghi nhận giới thiệu (ngày)
            <input
              className={inputClass}
              inputMode="numeric"
              max={3650}
              min={0}
              onChange={(event) => setAttributionWindowDays(event.target.value)}
              required
              type="number"
              value={attributionWindowDays}
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Thời gian chờ trước khi có thể rút (ngày)
            <input
              className={inputClass}
              inputMode="numeric"
              max={3650}
              min={0}
              onChange={(event) => setHoldDays(event.target.value)}
              required
              type="number"
              value={holdDays}
            />
          </label>
        </div>
        <fieldset className="space-y-3">
          <legend className="font-semibold">Mức hoa hồng theo dịch vụ</legend>
          <p className="text-sm text-[var(--theme-muted)]">
            Nhập tỷ lệ từ 0 đến 100%. Mỗi dịch vụ chỉ xuất hiện một lần.
          </p>
          <div className="space-y-3">
            {rates.map((rate, index) => (
              <div
                className="grid gap-3 rounded-lg border border-[var(--theme-border)] p-3 sm:grid-cols-[minmax(0,1fr)_minmax(10rem,0.7fr)_auto] sm:items-end"
                key={rate.id}
              >
                <label className="grid gap-1 text-sm font-semibold">
                  Dịch vụ
                  <select
                    className={inputClass}
                    onChange={(event) =>
                      setRates((current) =>
                        current.map((item) =>
                          item.id === rate.id
                            ? { ...item, serviceCode: event.target.value }
                            : item,
                        ),
                      )
                    }
                    required
                    value={rate.serviceCode}
                  >
                    <option value="">Chọn dịch vụ</option>
                    {services
                      .filter(
                        (service) =>
                          service.code === rate.serviceCode ||
                          !rates.some(
                            (item) => item.serviceCode === service.code,
                          ),
                      )
                      .map((service) => (
                        <option key={service.code} value={service.code}>
                          {service.label}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="grid gap-1 text-sm font-semibold">
                  Tỷ lệ hoa hồng (%)
                  <input
                    className={inputClass}
                    inputMode="decimal"
                    max="100"
                    min="0"
                    onChange={(event) =>
                      setRates((current) =>
                        current.map((item) =>
                          item.id === rate.id
                            ? { ...item, percent: event.target.value }
                            : item,
                        ),
                      )
                    }
                    placeholder="Ví dụ: 5"
                    required
                    step="0.01"
                    type="number"
                    value={rate.percent}
                  />
                </label>
                {rates.length > 1 ? (
                  <Button
                    aria-label={`Xóa mức hoa hồng thứ ${index + 1}`}
                    className="min-h-11"
                    onClick={() =>
                      setRates((current) =>
                        current.filter((item) => item.id !== rate.id),
                      )
                    }
                    type="button"
                    variant="outline"
                  >
                    Xóa
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
          {rates.length < services.length ? (
            <Button
              className="min-h-10"
              onClick={() => {
                const id = nextRateId.current++;
                setRates((current) => [
                  ...current,
                  { id, serviceCode: "", percent: "" },
                ]);
              }}
              type="button"
              variant="outline"
            >
              Thêm dịch vụ
            </Button>
          ) : null}
        </fieldset>
        <label className="flex min-h-11 items-center gap-2 text-sm font-semibold">
          <input
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
            type="checkbox"
          />
          Kích hoạt quy tắc sau khi phát hành
        </label>
        <Button
          className="min-h-11 sm:justify-self-start"
          disabled={create.isPending}
          type="submit"
        >
          {create.isPending ? "Đang tạo bản nháp…" : "Tạo bản nháp"}
        </Button>
      </form>
      {message ? (
        <p role="status" className="text-sm font-semibold text-emerald-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {rules.isPending ? (
        <p aria-busy="true" className="text-sm" role="status">
          Đang tải quy tắc…
        </p>
      ) : null}
      {rules.isError ? (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
          role="alert"
        >
          <p className="text-sm text-red-700">
            Chưa tải được danh sách quy tắc.
          </p>
          <Button
            className="min-h-10"
            onClick={() => void rules.refetch()}
            type="button"
            variant="outline"
          >
            Tải lại
          </Button>
        </div>
      ) : null}
      {rules.data?.length ? (
        <div className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)]">
          {rules.data.map((rule) => (
            <article
              className="flex flex-wrap items-center justify-between gap-3 p-4"
              key={rule.id}
            >
              <div>
                <p className="font-semibold">
                  Phiên bản {rule.versionNo} · {ruleStatusLabel(rule.status)} ·{" "}
                  {rule.enabled ? "Đang áp dụng" : "Chưa áp dụng"}
                </p>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">
                  Ghi nhận giới thiệu trong {rule.attributionWindowDays} ngày ·
                  chờ {rule.holdDays} ngày ·{" "}
                  {rule.rates
                    .map(
                      (rate) =>
                        `${affiliateServiceLabel(rate.serviceCode)}: ${basisPointsAsPercent(rate.directRateBasisPoints)}`,
                    )
                    .join(" · ")}
                </p>
              </div>
              {rule.status === "DRAFT" ? (
                <Button
                  className="min-h-10"
                  disabled={publish.isPending}
                  onClick={() => publish.mutate(rule.id)}
                  type="button"
                  variant="outline"
                >
                  Phát hành phiên bản
                </Button>
              ) : null}
            </article>
          ))}
        </div>
      ) : rules.data ? (
        <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
          Chưa có bộ quy tắc nào.
        </p>
      ) : null}
    </section>
  );
}
