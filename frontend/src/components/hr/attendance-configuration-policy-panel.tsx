"use client";

import { CircleAlert, MapPinned, ShieldCheck } from "lucide-react";
import dynamic from "next/dynamic";
import { type FormEvent, useState } from "react";

import type {
  AttendanceWorksite,
  AttendanceWorksitePolicy,
} from "@/lib/api/types";

import type { PolicyInput } from "./attendance-configuration-types";

const AttendanceLocationPicker = dynamic(
  () =>
    import("./attendance-location-picker").then(
      (module) => module.AttendanceLocationPicker,
    ),
  {
    loading: () => (
      <div
        aria-busy="true"
        aria-label="Đang tải bản đồ vùng chấm công"
        className="mt-5 h-72 animate-pulse rounded-2xl bg-neutral-100 sm:h-96"
      />
    ),
    ssr: false,
  },
);

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-neutral-100";

type PolicyQuery = {
  data?: { data: AttendanceWorksitePolicy[]; meta: { total: number } };
  isPending: boolean;
  isError: boolean;
};

type PolicyForm = {
  effectiveFrom: string;
  effectiveTo: string;
  timezone: string;
  latitude: string;
  longitude: string;
  radiusMeters: string;
  maxAccuracyMeters: string;
};

const emptyPolicyForm: PolicyForm = {
  effectiveFrom: "",
  effectiveTo: "",
  timezone: "",
  latitude: "",
  longitude: "",
  radiusMeters: "",
  maxAccuracyMeters: "",
};

export function AttendancePolicyPanel({
  isSaving,
  onRetry,
  onSave,
  policies,
  selectedWorksite,
}: {
  isSaving: boolean;
  onRetry: () => void;
  onSave: (input: PolicyInput) => Promise<unknown>;
  policies: PolicyQuery;
  selectedWorksite: AttendanceWorksite | null;
}) {
  const [draft, setDraft] = useState<PolicyForm | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const canConfigure = selectedWorksite?.status === "ACTIVE";
  const rows = policies.data?.data ?? [];
  const latestPolicy = rows[0] ?? null;
  const inheritedInputs: PolicyForm = latestPolicy
    ? {
        ...emptyPolicyForm,
        timezone: latestPolicy.timezone,
        latitude: latestPolicy.latitude,
        longitude: latestPolicy.longitude,
        radiusMeters: String(latestPolicy.radiusMeters),
        maxAccuracyMeters: String(latestPolicy.maxAccuracyMeters),
      }
    : emptyPolicyForm;
  const form = draft ?? inheritedInputs;
  const {
    effectiveFrom,
    effectiveTo,
    timezone,
    latitude,
    longitude,
    radiusMeters,
    maxAccuracyMeters,
  } = form;

  function updateInput(field: keyof PolicyForm, value: string) {
    setDraft((current) => ({
      ...(current ?? inheritedInputs),
      [field]: value,
    }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const radius = Number(radiusMeters);
    const accuracy = Number(maxAccuracyMeters);
    if (
      !canConfigure ||
      !effectiveFrom ||
      !timezone.trim() ||
      !latitude.trim() ||
      !longitude.trim() ||
      !Number.isFinite(radius) ||
      radius <= 0 ||
      !Number.isFinite(accuracy) ||
      accuracy <= 0
    ) {
      setFormError("Nhập đầy đủ giá trị GPS dương cho chính sách này.");
      return;
    }
    if (effectiveTo && effectiveTo < effectiveFrom) {
      setFormError("Ngày kết thúc không được trước ngày hiệu lực.");
      return;
    }
    try {
      await onSave({
        effectiveFrom,
        effectiveTo: effectiveTo || null,
        timezone: timezone.trim(),
        latitude: latitude.trim(),
        longitude: longitude.trim(),
        radiusMeters: radius,
        maxAccuracyMeters: accuracy,
      });
      setDraft(emptyPolicyForm);
    } catch {
      setFormError(
        "Không thể lưu chính sách. Kiểm tra múi giờ, tọa độ và khoảng hiệu lực.",
      );
    }
  }

  return (
    <section
      aria-labelledby="attendance-policy-title"
      className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm sm:p-6"
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
          <MapPinned aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            02 · Vùng chấm công
          </p>
          <h2
            className="mt-1 text-xl font-bold text-neutral-950"
            id="attendance-policy-title"
          >
            Thiết lập vùng chấm công
          </h2>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            {selectedWorksite
              ? `Thiết lập tâm vùng, bán kính và độ chính xác cho ${selectedWorksite.name}.`
              : "Chọn một địa điểm trước khi thiết lập vùng chấm công."}
          </p>
        </div>
      </div>

      <form
        className="mt-5 rounded-2xl bg-neutral-50 p-4 sm:p-5"
        onSubmit={submit}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-effective-from"
          >
            Ngày hiệu lực
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-effective-from"
              onChange={(event) =>
                updateInput("effectiveFrom", event.target.value)
              }
              type="date"
              value={effectiveFrom}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-effective-to"
          >
            Kết thúc{" "}
            <span className="font-normal text-neutral-500">(nếu có)</span>
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-effective-to"
              min={effectiveFrom || undefined}
              onChange={(event) =>
                updateInput("effectiveTo", event.target.value)
              }
              type="date"
              value={effectiveTo}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800 sm:col-span-2"
            htmlFor="attendance-policy-timezone"
          >
            Múi giờ IANA
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-timezone"
              maxLength={64}
              onChange={(event) => updateInput("timezone", event.target.value)}
              placeholder="VD: Asia/Ho_Chi_Minh"
              value={timezone}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-latitude"
          >
            Vĩ độ
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-latitude"
              inputMode="decimal"
              onChange={(event) => updateInput("latitude", event.target.value)}
              placeholder="10.7769"
              value={latitude}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-longitude"
          >
            Kinh độ
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-longitude"
              inputMode="decimal"
              onChange={(event) => updateInput("longitude", event.target.value)}
              placeholder="106.7009"
              value={longitude}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-radius"
          >
            Bán kính cho phép (m)
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-radius"
              inputMode="numeric"
              min="1"
              onChange={(event) =>
                updateInput("radiusMeters", event.target.value)
              }
              type="number"
              value={radiusMeters}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-policy-accuracy"
          >
            Sai số GPS tối đa (m)
            <input
              className={fieldClass}
              disabled={!canConfigure}
              id="attendance-policy-accuracy"
              inputMode="numeric"
              min="1"
              onChange={(event) =>
                updateInput("maxAccuracyMeters", event.target.value)
              }
              type="number"
              value={maxAccuracyMeters}
            />
          </label>
        </div>
        <AttendanceLocationPicker
          disabled={!canConfigure}
          latitude={latitude}
          longitude={longitude}
          onCoordinatesChange={(nextLatitude, nextLongitude) => {
            setDraft((current) => ({
              ...(current ?? inheritedInputs),
              latitude: nextLatitude,
              longitude: nextLongitude,
            }));
          }}
          radiusMeters={radiusMeters}
        />
        {latestPolicy ? (
          <p className="mt-3 text-sm leading-6 text-primary-900">
            Đã sao chép thông số từ chính sách gần nhất. Hãy chọn ngày hiệu lực
            cho phiên bản mới.
          </p>
        ) : null}
        {selectedWorksite && !canConfigure ? (
          <p className="mt-3 text-sm text-amber-800">
            Địa điểm đang tạm ngưng; hãy kích hoạt lại trước khi tạo chính sách
            mới.
          </p>
        ) : null}
        {formError ? (
          <p className="mt-3 flex gap-2 text-sm text-rose-700" role="alert">
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            {formError}
          </p>
        ) : null}
        <button
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-primary-700 px-4 text-sm font-bold text-white transition hover:bg-primary-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSaving || !canConfigure}
          type="submit"
        >
          {isSaving ? "Đang lưu..." : "Lưu chính sách"}
        </button>
      </form>

      <div className="mt-5" aria-live="polite">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-neutral-950">
            Lịch sử chính sách
          </h3>
          <span className="text-xs font-semibold text-neutral-500">
            {policies.data?.meta.total ?? 0} bản ghi
          </span>
        </div>
        {policies.isPending ? (
          <div
            aria-busy="true"
            className="mt-3 h-24 animate-pulse rounded-xl bg-neutral-100"
          />
        ) : null}
        {policies.isError ? (
          <p
            className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
            role="alert"
          >
            Không thể tải chính sách.
            <button
              className="ml-2 font-bold underline"
              onClick={onRetry}
              type="button"
            >
              Thử lại
            </button>
          </p>
        ) : null}
        {!policies.isPending &&
        !policies.isError &&
        selectedWorksite &&
        rows.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-neutral-300 p-4 text-sm leading-6 text-neutral-600">
            Chưa có chính sách. Hệ thống sẽ chưa cho phép phân công mới tại địa
            điểm này.
          </p>
        ) : null}
        <ul className="mt-3 space-y-3" role="list">
          {rows.map((policy) => (
            <PolicyHistoryItem key={policy.id} policy={policy} />
          ))}
        </ul>
      </div>
    </section>
  );
}

function PolicyHistoryItem({ policy }: { policy: AttendanceWorksitePolicy }) {
  return (
    <li className="rounded-xl border border-neutral-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-bold text-neutral-950">
            {policy.timezone}
          </p>
          <p className="mt-1 text-sm text-neutral-600">
            Từ {policy.effectiveFrom}
            {policy.effectiveTo
              ? ` đến ${policy.effectiveTo}`
              : " · chưa có ngày kết thúc"}
          </p>
        </div>
        <span className="rounded-full bg-primary-50 px-2.5 py-1 text-xs font-bold text-primary-800">
          {policy.radiusMeters} m · sai số {policy.maxAccuracyMeters} m
        </span>
      </div>
      <details className="mt-3 text-sm text-neutral-600">
        <summary className="cursor-pointer font-semibold text-neutral-800">
          Xem tọa độ quản trị
        </summary>
        <p className="mt-2">
          Vĩ độ {policy.latitude} · Kinh độ {policy.longitude}
        </p>
      </details>
      <p className="mt-3 flex gap-2 text-xs leading-5 text-neutral-500">
        <ShieldCheck
          aria-hidden="true"
          className="size-4 shrink-0 text-primary-700"
        />
        Bản ghi lịch sử không thể chỉnh sửa hoặc xóa tại đây.
      </p>
    </li>
  );
}
