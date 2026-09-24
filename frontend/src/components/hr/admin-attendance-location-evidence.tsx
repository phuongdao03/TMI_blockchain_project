"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin, RefreshCw, ShieldCheck } from "lucide-react";
import dynamic from "next/dynamic";

import { ApiError, hrAdminAttendanceApi } from "@/lib/api/client";
import type { AttendanceLocationEvidenceReview } from "@/lib/api/types";

const AttendanceEvidenceMap = dynamic(
  () =>
    import("./attendance-evidence-map").then(
      (module) => module.AttendanceEvidenceMap,
    ),
  {
    ssr: false,
    loading: () => (
      <div
        aria-label="Đang tải bản đồ"
        className="h-64 animate-pulse rounded-xl bg-neutral-100"
      />
    ),
  },
);

const outcomeLabels: Record<
  AttendanceLocationEvidenceReview["outcome"],
  string
> = {
  ACCEPTED: "Đạt điều kiện",
  OUTSIDE_WORKSITE: "Ngoài vùng chấm công",
  LOW_ACCURACY: "Sai số GPS vượt giới hạn",
  LOCATION_UNAVAILABLE: "Không lấy được vị trí",
  EXCEPTION_APPROVED: "Ngoại lệ đã duyệt",
};

function formatDateTime(value: string, timeZone: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone,
  }).format(new Date(value));
}

export function AdminAttendanceLocationEvidence({
  attendanceId,
  employeeName,
}: {
  attendanceId: string;
  employeeName: string;
}) {
  const evidence = useQuery({
    queryKey: ["hr", "admin", "attendance-location-evidence", attendanceId],
    queryFn: () => hrAdminAttendanceApi.listLocationEvidence(attendanceId),
    gcTime: 0,
    retry: false,
    staleTime: 0,
  });
  const rows = evidence.data ?? [];
  const hasCoordinates = rows.some(
    (item) => item.latitude !== null && item.longitude !== null,
  );

  return (
    <section
      aria-label={`Bằng chứng GPS của ${employeeName}`}
      className="attendance-evidence-panel space-y-4 rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-900 dark:bg-neutral-950 sm:p-5"
    >
      <div className="flex items-start gap-3">
        <ShieldCheck
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-emerald-700"
        />
        <div>
          <h3 className="text-base font-bold text-neutral-950 dark:text-white">
            Vị trí chấm công · {employeeName}
          </h3>
          <p className="mt-1 text-sm leading-6 text-neutral-700 dark:text-neutral-300">
            Chỉ Super Admin xem được bằng chứng GPS trên bản đồ. Dữ liệu vị trí
            được xóa sau 24 tháng theo chính sách lưu giữ.
          </p>
        </div>
      </div>

      {evidence.isPending ? (
        <div
          aria-label="Đang tải bằng chứng GPS"
          className="h-24 animate-pulse rounded-lg bg-emerald-100"
        />
      ) : null}
      {evidence.isError ? (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-3"
          role="alert"
        >
          <p className="text-sm font-semibold text-red-900">
            {evidence.error instanceof ApiError
              ? evidence.error.message
              : "Không thể tải bằng chứng GPS. Vui lòng thử lại."}
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
        <p className="rounded-lg border border-dashed border-neutral-300 bg-white p-4 text-sm text-neutral-700">
          Lượt chấm công này chưa có bằng chứng vị trí.
        </p>
      ) : null}

      {hasCoordinates ? <AttendanceEvidenceMap evidence={rows} /> : null}

      {rows.map((item) => (
        <article
          className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900"
          key={item.id}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="inline-flex items-center gap-2 text-sm font-bold text-neutral-950 dark:text-white">
              <MapPin aria-hidden="true" className="size-4 text-primary-700" />
              {item.eventType === "CHECK_IN" ? "Chấm công vào" : "Chấm công ra"}
            </h4>
            <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100">
              {outcomeLabels[item.outcome]}
            </span>
          </div>
          <p className="mt-2 text-xs text-neutral-600 dark:text-neutral-300">
            {formatDateTime(item.clientCapturedAt, item.effectiveTimezone)} ·{" "}
            {item.worksiteName}
          </p>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <Metric
              label="Độ chính xác GPS"
              value={`${item.accuracyMeters} m · giới hạn ${item.maxAccuracyMeters} m`}
            />
            <Metric
              label="Khoảng cách tới điểm làm việc"
              value={`${item.distanceMeters} m · bán kính ${item.permittedRadiusMeters} m`}
            />
            <Metric label="Múi giờ" value={item.effectiveTimezone} />
          </dl>
        </article>
      ))}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-neutral-600 dark:text-neutral-300">
        {label}
      </dt>
      <dd className="mt-1 break-words font-medium text-neutral-900 dark:text-neutral-100">
        {value}
      </dd>
    </div>
  );
}
