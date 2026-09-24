"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock3, MapPin, RefreshCw, ShieldCheck, X } from "lucide-react";
import dynamic from "next/dynamic";

import { ApiError, hrSelfApi } from "@/lib/api/client";
import type { AttendanceLocationOutcome } from "@/lib/api/types";

const AttendanceEvidenceMap = dynamic(
  () =>
    import("./attendance-evidence-map").then(
      (module) => module.AttendanceEvidenceMap,
    ),
  {
    ssr: false,
    loading: () => (
      <div
        aria-label="Đang tải bản đồ vị trí chấm công"
        className="h-56 animate-pulse rounded-xl bg-neutral-100"
      />
    ),
  },
);

const outcomeLabels: Record<AttendanceLocationOutcome, string> = {
  ACCEPTED: "Đạt điều kiện",
  OUTSIDE_WORKSITE: "Ngoài bán kính",
  LOW_ACCURACY: "Độ chính xác GPS thấp",
  LOCATION_UNAVAILABLE: "Không lấy được vị trí",
  EXCEPTION_APPROVED: "Ngoại lệ đã duyệt",
};

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể tải bằng chứng vị trí. Vui lòng thử lại.";
}

function formatEvidenceTime(value: string, timeZone: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone,
  }).format(new Date(value));
}

export function PersonalAttendanceLocationEvidence({
  attendanceId,
  onClose,
}: {
  attendanceId: string;
  onClose: () => void;
}) {
  const evidence = useQuery({
    queryKey: ["hr", "self", "attendance-location-evidence", attendanceId],
    queryFn: () => hrSelfApi.listLocationEvidence(attendanceId),
  });
  const rows = evidence.data ?? [];

  return (
    <section
      aria-labelledby="personal-location-evidence-title"
      className="attendance-personal-evidence mt-4 rounded-xl border p-4"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-primary-800">
            <ShieldCheck aria-hidden="true" className="size-4" /> Bằng chứng
            riêng tư
          </p>
          <h3
            className="mt-2 text-base font-bold text-neutral-950"
            id="personal-location-evidence-title"
          >
            Bằng chứng vị trí của bạn
          </h3>
        </div>
        <button
          aria-label="Đóng bằng chứng vị trí"
          className="rounded-lg p-2 text-neutral-600 transition hover:bg-white"
          onClick={onClose}
          type="button"
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      </div>
      <p className="mt-2 text-sm leading-6 text-neutral-700">
        Vị trí được thể hiện trực quan trên bản đồ. Hệ thống không hiển thị tọa
        độ chi tiết và không đưa dữ liệu vị trí vào thông báo hoặc báo cáo
        chung.
      </p>

      {evidence.isPending ? (
        <div
          aria-busy="true"
          aria-label="Đang tải bằng chứng vị trí"
          className="mt-4 h-24 animate-pulse rounded-lg bg-primary-100"
        />
      ) : null}
      {evidence.isError ? (
        <div
          className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3"
          role="alert"
        >
          <p className="text-sm font-semibold text-red-900">
            {apiMessage(evidence.error)}
          </p>
          <button
            className="mt-2 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-red-900"
            onClick={() => void evidence.refetch()}
            type="button"
          >
            <RefreshCw aria-hidden="true" className="size-4" /> Thử lại
          </button>
        </div>
      ) : null}
      {!evidence.isPending && !evidence.isError && rows.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-primary-300 bg-white p-4 text-sm text-neutral-700">
          Chưa có bằng chứng vị trí cho lượt chấm công này.
        </p>
      ) : null}
      {rows.some(
        (item) => item.latitude !== null && item.longitude !== null,
      ) ? (
        <div className="mt-4">
          <AttendanceEvidenceMap evidence={rows} />
        </div>
      ) : null}
      <div className="mt-4 space-y-3">
        {rows.map((item) => (
          <article
            className="rounded-lg border border-primary-100 bg-white p-3"
            key={item.id}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="inline-flex items-center gap-2 text-sm font-bold text-neutral-950">
                <MapPin
                  aria-hidden="true"
                  className="size-4 text-primary-700"
                />
                {item.eventType === "CHECK_IN" ? "Giờ vào" : "Giờ ra"}
              </p>
              <span className="rounded-full bg-primary-50 px-2.5 py-1 text-xs font-bold text-primary-900">
                {outcomeLabels[item.outcome]}
              </span>
            </div>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <EvidenceMetric
                label="Điểm chấm công"
                value={item.worksiteName}
              />
              <EvidenceMetric
                icon={Clock3}
                label="Thời gian ghi nhận"
                value={formatEvidenceTime(
                  item.clientCapturedAt,
                  item.effectiveTimezone,
                )}
              />
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidenceMetric({
  icon: Icon,
  label,
  value,
}: {
  icon?: typeof Clock3;
  label: string;
  value: string;
}) {
  return (
    <div>
      <dt className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-neutral-500">
        {Icon ? <Icon aria-hidden="true" className="size-3.5" /> : null}
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-semibold text-neutral-900">
        {value}
      </dd>
    </div>
  );
}
