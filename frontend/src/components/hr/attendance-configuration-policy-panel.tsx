"use client";

import { CircleAlert, MapPinned, ShieldCheck } from "lucide-react";
import dynamic from "next/dynamic";
import { type FormEvent, useState } from "react";

import type {
  AttendanceWorksite,
  AttendanceWorksitePolicy,
} from "@/lib/api/types";

import type {
  PolicyCorrectionInput,
  PolicyInput,
} from "./attendance-configuration-types";

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

function localDateIn(timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: string) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

export function AttendancePolicyPanel({
  isSaving,
  onCorrect,
  onRetry,
  onSave,
  policies,
  selectedWorksite,
}: {
  isSaving: boolean;
  onCorrect: (
    policyId: string,
    input: PolicyCorrectionInput,
  ) => Promise<unknown>;
  onRetry: () => void;
  onSave: (input: PolicyInput) => Promise<unknown>;
  policies: PolicyQuery;
  selectedWorksite: AttendanceWorksite | null;
}) {
  const [draft, setDraft] = useState<PolicyForm | null>(null);
  const [correcting, setCorrecting] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [correctionReason, setCorrectionReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const canConfigure = selectedWorksite?.status === "ACTIVE";
  const rows = policies.data?.data ?? [];
  const latestPolicy = rows[0] ?? null;
  const correctablePolicy =
    rows.find((policy) => {
      const today = localDateIn(policy.timezone);
      return (
        policy.effectiveFrom <= today &&
        (!policy.effectiveTo || policy.effectiveTo >= today)
      );
    }) ??
    rows.find(
      (policy) => policy.effectiveFrom > localDateIn(policy.timezone),
    ) ??
    null;
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
  const showForm =
    Boolean(selectedWorksite) &&
    (!latestPolicy || correcting || creatingVersion);
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
    const parsedLatitude = Number(latitude);
    const parsedLongitude = Number(longitude);
    if (
      !canConfigure ||
      (!correcting && !effectiveFrom) ||
      !timezone.trim() ||
      !latitude.trim() ||
      !longitude.trim() ||
      !Number.isFinite(parsedLatitude) ||
      parsedLatitude < -90 ||
      parsedLatitude > 90 ||
      !Number.isFinite(parsedLongitude) ||
      parsedLongitude < -180 ||
      parsedLongitude > 180 ||
      !Number.isFinite(radius) ||
      radius <= 0 ||
      !Number.isFinite(accuracy) ||
      accuracy <= 0
    ) {
      setFormError("Kiểm tra tọa độ hợp lệ, bán kính và sai số GPS lớn hơn 0.");
      return;
    }
    if (correcting && correctionReason.trim().length < 10) {
      setFormError(
        "Nhập lý do điều chỉnh ít nhất 10 ký tự để lưu vào nhật ký.",
      );
      return;
    }
    if (effectiveTo && effectiveTo < effectiveFrom) {
      setFormError("Ngày kết thúc không được trước ngày hiệu lực.");
      return;
    }
    try {
      if (correcting && correctablePolicy) {
        await onCorrect(correctablePolicy.id, {
          latitude: latitude.trim(),
          longitude: longitude.trim(),
          radiusMeters: radius,
          maxAccuracyMeters: accuracy,
          reason: correctionReason.trim(),
        });
        setCorrecting(false);
        setCreatingVersion(false);
        setCorrectionReason("");
        setDraft(null);
        return;
      }
      await onSave({
        effectiveFrom,
        effectiveTo: effectiveTo || null,
        timezone: timezone.trim(),
        latitude: latitude.trim(),
        longitude: longitude.trim(),
        radiusMeters: radius,
        maxAccuracyMeters: accuracy,
      });
      setDraft(null);
      setCreatingVersion(false);
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
      <div className="flex flex-wrap items-start gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
          <MapPinned aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
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
              ? `Chọn ngày hiệu lực, xác nhận tâm vùng trên bản đồ và nhập bán kính cho ${selectedWorksite.name}.`
              : "Chọn một địa điểm ở bước 1 trước khi thiết lập vùng chấm công."}
          </p>
        </div>
        {latestPolicy && canConfigure ? (
          <button
            className="min-h-11 rounded-xl border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)]"
            onClick={() => {
              setCreatingVersion((current) => !current);
              setCorrecting(false);
              setDraft(null);
              setFormError(null);
            }}
            type="button"
          >
            {creatingVersion ? "Hủy phiên bản mới" : "Tạo phiên bản mới"}
          </button>
        ) : null}
        {correctablePolicy && canConfigure ? (
          <button
            className="min-h-11 rounded-xl border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)]"
            onClick={() => {
              setCorrecting((current) => !current);
              setCreatingVersion(false);
              setDraft(
                correcting
                  ? null
                  : {
                      effectiveFrom: correctablePolicy.effectiveFrom,
                      effectiveTo: correctablePolicy.effectiveTo ?? "",
                      timezone: correctablePolicy.timezone,
                      latitude: correctablePolicy.latitude,
                      longitude: correctablePolicy.longitude,
                      radiusMeters: String(correctablePolicy.radiusMeters),
                      maxAccuracyMeters: String(
                        correctablePolicy.maxAccuracyMeters,
                      ),
                    },
              );
              setFormError(null);
            }}
            type="button"
          >
            {correcting ? "Hủy sửa vị trí" : "Sửa vị trí đã lưu"}
          </button>
        ) : null}
      </div>

      {latestPolicy && !showForm ? (
        <p className="mt-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 text-sm leading-6 text-[var(--theme-text)]">
          Vùng đã lưu: {latestPolicy.latitude}, {latestPolicy.longitude} · bán
          kính {latestPolicy.radiusMeters} m · sai số tối đa{" "}
          {latestPolicy.maxAccuracyMeters} m. Chọn sửa vị trí nếu đặt nhầm tâm
          vùng; chọn phiên bản mới khi cần thay đổi thời gian áp dụng.
        </p>
      ) : null}

      {correcting ? (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
          Sửa tâm vùng, bán kính hoặc sai số của chính sách hiện tại. Ngày hiệu
          lực và múi giờ được giữ nguyên; lý do và giá trị trước/sau được ghi
          vào nhật ký quản trị.
        </p>
      ) : null}

      {showForm ? (
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
                disabled={!canConfigure || correcting}
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
                disabled={!canConfigure || correcting}
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
                disabled={!canConfigure || correcting}
                id="attendance-policy-timezone"
                list="attendance-timezone-options"
                maxLength={64}
                onChange={(event) =>
                  updateInput("timezone", event.target.value)
                }
                placeholder="VD: Asia/Ho_Chi_Minh"
                value={timezone}
              />
            </label>
            <datalist id="attendance-timezone-options">
              <option value="Asia/Ho_Chi_Minh" />
              <option value="Asia/Singapore" />
              <option value="Asia/Bangkok" />
            </datalist>
          </div>
          {correcting ? (
            <label
              className="mt-4 block text-sm font-semibold text-neutral-800"
              htmlFor="attendance-policy-correction-reason"
            >
              Lý do điều chỉnh
              <textarea
                className={fieldClass}
                id="attendance-policy-correction-reason"
                maxLength={500}
                minLength={10}
                onChange={(event) => setCorrectionReason(event.target.value)}
                placeholder="Ví dụ: Đã chọn nhầm vị trí khi thiết lập ban đầu"
                required
                rows={2}
                value={correctionReason}
              />
            </label>
          ) : null}
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
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
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
                onChange={(event) =>
                  updateInput("latitude", event.target.value)
                }
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
                onChange={(event) =>
                  updateInput("longitude", event.target.value)
                }
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
          {latestPolicy && !correcting ? (
            <p className="mt-3 text-sm leading-6 text-primary-900">
              Đã sao chép thông số từ chính sách gần nhất. Hãy chọn ngày hiệu
              lực cho phiên bản mới.
            </p>
          ) : null}
          {selectedWorksite && !canConfigure ? (
            <p className="mt-3 text-sm text-amber-800">
              Địa điểm đang tạm ngưng; hãy kích hoạt lại trước khi tạo chính
              sách mới.
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
            {isSaving
              ? "Đang lưu..."
              : correcting
                ? "Lưu tọa độ sửa"
                : "Lưu chính sách"}
          </button>
        </form>
      ) : null}

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
        Chính sách cũ được lưu để đối chiếu. Chỉ chính sách hiện tại được sửa
        tọa độ và mọi lần sửa đều có nhật ký.
      </p>
    </li>
  );
}
