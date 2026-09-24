"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  Check,
  CircleAlert,
  Clock3,
  LogIn,
  LogOut,
  MapPinned,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { ApiError, hrSelfApi } from "@/lib/api/client";
import {
  captureForegroundLocation,
  LocationCaptureError,
} from "@/lib/geolocation";
import type { Attendance, AttendanceStatus } from "@/lib/api/types";
import { PersonalAttendanceLocationEvidence } from "@/components/hr/personal-attendance-location-evidence";

const statusPresentation: Record<
  AttendanceStatus,
  { label: string; className: string }
> = {
  PRESENT: { label: "Đúng giờ", className: "bg-emerald-50 text-emerald-800" },
  LATE: { label: "Đi muộn", className: "bg-amber-50 text-amber-900" },
  ABSENT: { label: "Vắng mặt", className: "bg-red-50 text-red-800" },
  LEAVE: { label: "Nghỉ phép", className: "bg-violet-50 text-violet-800" },
  HALF_DAY: { label: "Nửa ngày", className: "bg-amber-50 text-amber-900" },
  OT: { label: "Tăng ca", className: "bg-sky-50 text-sky-800" },
  PENDING: {
    label: "Chờ duyệt vị trí",
    className: "bg-amber-50 text-amber-900 ring-1 ring-amber-200",
  },
  REJECTED: {
    label: "Từ chối vị trí",
    className: "bg-red-50 text-red-800 ring-1 ring-red-200",
  },
};

function formatTime(value: string | null, timezone?: string) {
  if (!value) return "Chưa ghi nhận";
  const options: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
  };
  if (timezone) options.timeZone = timezone;
  return new Intl.DateTimeFormat("vi-VN", options).format(new Date(value));
}

function formatWorkdayDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function evidenceActionDate(value: string) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function errorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof LocationCaptureError
    ? error.message
    : "Không thể cập nhật chấm công. Vui lòng thử lại.";
}

export function AttendanceWorkspace() {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [locationSummary, setLocationSummary] = useState<string | null>(null);
  const [isCapturingLocation, setIsCapturingLocation] = useState(false);
  const [showLocationEvidence, setShowLocationEvidence] = useState(false);
  const attendance = useQuery({
    queryKey: ["hr", "self", "attendance"],
    queryFn: () => hrSelfApi.listAttendance({ pageSize: 20 }),
  });
  const workdayContext = useQuery({
    queryKey: ["hr", "self", "attendance-workday-context"],
    queryFn: () => hrSelfApi.getWorkdayContext(),
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["hr", "self", "attendance"] }),
      queryClient.invalidateQueries({
        queryKey: ["hr", "self", "attendance-workday-context"],
      }),
    ]);
  async function captureLocation() {
    setNotice(null);
    setLocationSummary(null);
    setIsCapturingLocation(true);
    try {
      const location = await captureForegroundLocation();
      setLocationSummary(
        `Vị trí đã được ghi nhận từ thiết bị; sai số báo cáo là ${Math.round(location.accuracyMeters)} m.`,
      );
      return location;
    } finally {
      setIsCapturingLocation(false);
    }
  }
  const checkIn = useMutation({
    mutationFn: async () => {
      const location = await captureLocation();
      return hrSelfApi.checkIn({ ...location, note: note.trim() || null });
    },
    onSuccess: (record) => {
      setNote("");
      setNotice(
        record.status === "PENDING"
          ? "Yêu cầu chấm công vào đã được ghi nhận và đang chờ Super Admin xét duyệt vị trí."
          : "Chấm công vào thành công. Thời gian máy chủ và vị trí đã được lưu an toàn.",
      );
      void refresh();
    },
  });
  const checkOut = useMutation({
    mutationFn: async () => hrSelfApi.checkOut(await captureLocation()),
    onSuccess: (record) => {
      setNotice(
        record.status === "PENDING"
          ? "Yêu cầu chấm công ra đã được ghi nhận và đang chờ Super Admin xét duyệt vị trí."
          : "Chấm công ra thành công. Ngày làm việc của bạn đã được cập nhật.",
      );
      void refresh();
    },
  });
  const rows = attendance.data?.data ?? [];
  const workday = workdayContext.data;
  const hasActiveWorkday = Boolean(workday?.workDate && workday.timezone);
  const today = workday?.workDate
    ? rows.find((item) => item.workDate === workday.workDate)
    : undefined;
  const isSaving =
    isCapturingLocation || checkIn.isPending || checkOut.isPending;
  const actionError = checkIn.error ?? checkOut.error;
  const todayPresentation = today ? statusPresentation[today.status] : null;

  return (
    <section
      aria-labelledby="attendance-title"
      className="mx-auto max-w-6xl space-y-6 pb-12"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.2),transparent_65%)]" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <Clock3 aria-hidden="true" className="size-4" /> Thời gian làm
              việc
            </p>
            <h1
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
              id="attendance-title"
            >
              Chấm công cá nhân
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Ghi nhận giờ vào và ra bằng thời gian máy chủ. Ca làm, ngày lễ và
              quy tắc đi muộn sẽ được áp dụng sau khi được cấu hình.
            </p>
          </div>
          <p className="inline-flex items-center gap-2 self-start rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-100 sm:self-auto">
            <CalendarDays
              aria-hidden="true"
              className="size-4 text-emerald-300"
            />
            {workday?.workDate
              ? formatWorkdayDate(workday.workDate)
              : workdayContext.isPending
                ? "Đang xác định ngày công"
                : "Chưa có ngày công được cấu hình"}
          </p>
        </div>
      </header>

      {attendance.isPending ? <AttendanceSkeleton /> : null}
      {attendance.isError ? (
        <AttendanceError
          error={attendance.error}
          onRetry={() => void attendance.refetch()}
        />
      ) : null}

      {attendance.isSuccess ? (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section
            aria-labelledby="today-title"
            className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
                  Hôm nay
                </p>
                <h2
                  className="mt-2 text-2xl font-bold tracking-tight text-neutral-950"
                  id="today-title"
                >
                  {today?.checkOutAt
                    ? "Ca làm đã hoàn tất"
                    : today
                      ? "Bạn đang trong ca"
                      : "Sẵn sàng bắt đầu"}
                </h2>
              </div>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold ${todayPresentation?.className ?? "bg-neutral-100 text-neutral-700"}`}
              >
                {today?.status === "PENDING" || today?.status === "REJECTED" ? (
                  <CircleAlert aria-hidden="true" className="size-3.5" />
                ) : (
                  <Check aria-hidden="true" className="size-3.5" />
                )}
                {todayPresentation?.label ?? "Chưa chấm công"}
              </span>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <TimeTile
                label="Giờ vào"
                value={formatTime(
                  today?.checkInAt ?? null,
                  workday?.timezone ?? undefined,
                )}
              />
              <TimeTile
                label="Giờ ra"
                value={formatTime(
                  today?.checkOutAt ?? null,
                  workday?.timezone ?? undefined,
                )}
              />
            </div>
            {workday?.timezone ? (
              <p className="mt-3 text-xs font-semibold text-neutral-500">
                Ngày công theo {workday.timezone}
              </p>
            ) : null}
            <div className="attendance-primary-action mt-5 rounded-2xl border p-4 sm:flex sm:items-center sm:justify-between sm:gap-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
                  Thao tác chấm công
                </p>
                <p className="mt-1 text-sm leading-6 text-neutral-700">
                  {!hasActiveWorkday
                    ? "Admin cần cấu hình địa điểm làm việc trước khi bạn có thể chấm công."
                    : today?.checkOutAt
                      ? "Giờ vào và giờ ra hôm nay đã được ghi nhận."
                      : today
                        ? "Xác nhận kết thúc ca và ghi nhận vị trí hiện tại."
                        : "Ghi nhận giờ vào và vị trí hiện tại của bạn."}
                </p>
              </div>
              <div className="mt-3 shrink-0 sm:mt-0">
                {!today ? (
                  <ActionButton
                    disabled={isSaving || !hasActiveWorkday}
                    icon={LogIn}
                    label={
                      !hasActiveWorkday
                        ? "Chưa thể chấm công vào"
                        : isCapturingLocation
                          ? "Đang lấy vị trí GPS..."
                          : isSaving
                            ? "Đang ghi nhận..."
                            : "Chấm công vào"
                    }
                    onClick={() => checkIn.mutate()}
                  />
                ) : null}
                {today && !today.checkOutAt ? (
                  <ActionButton
                    disabled={isSaving || !hasActiveWorkday}
                    icon={LogOut}
                    label={
                      isCapturingLocation
                        ? "Đang lấy vị trí GPS..."
                        : isSaving
                          ? "Đang cập nhật..."
                          : "Chấm công ra"
                    }
                    onClick={() => checkOut.mutate()}
                  />
                ) : null}
                {today?.checkOutAt ? (
                  <p className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-emerald-50 px-4 text-sm font-bold text-emerald-800">
                    <Check aria-hidden="true" className="size-4" />
                    Đã hoàn tất ngày công
                  </p>
                ) : null}
              </div>
            </div>
            {workdayContext.isError ? (
              <aside
                className="mt-4 flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-950"
                role="alert"
              >
                <CircleAlert
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-red-800"
                />
                <p>
                  Không thể xác định ngày công theo địa điểm làm việc. Vui lòng
                  thử lại hoặc liên hệ Super Admin; hệ thống chưa tự suy đoán
                  ngày từ trình duyệt.
                </p>
              </aside>
            ) : null}
            {workdayContext.isSuccess && !hasActiveWorkday ? (
              <aside
                className="mt-4 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"
                role="status"
              >
                <CircleAlert
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-amber-800"
                />
                <p>
                  Chưa có địa điểm làm việc và chính sách chấm công hiệu lực.
                  Bạn chưa thể ghi nhận chấm công; hãy liên hệ Super Admin.
                </p>
              </aside>
            ) : null}
            {!today && hasActiveWorkday ? (
              <label className="mt-5 block text-sm font-bold text-neutral-800">
                Ghi chú ngày công{" "}
                <span className="font-normal text-neutral-500">
                  (không bắt buộc)
                </span>
                <textarea
                  className="mt-2 min-h-24 w-full rounded-xl border border-neutral-300 bg-white px-3 py-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                  maxLength={2000}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Ví dụ: Làm việc tại văn phòng Hà Nội"
                  value={note}
                />
              </label>
            ) : null}
            <aside className="mt-5 flex gap-3 rounded-xl border border-primary-100 bg-primary-50 p-4 text-sm leading-6 text-primary-950">
              <Clock3
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0 text-primary-700"
              />
              <p>
                Vị trí thiết bị là bắt buộc khi chấm công vào hoặc ra. Hệ thống
                chỉ lấy một mẫu sau khi bạn bấm nút, không theo dõi liên tục và
                luôn ghi nhận độ chính xác do thiết bị cung cấp.
              </p>
            </aside>
            {today?.status === "PENDING" ? (
              <aside
                className="mt-4 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"
                role="status"
              >
                <CircleAlert
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-amber-800"
                />
                <p>
                  Vị trí đang chờ Super Admin duyệt. Lượt chấm công này chưa
                  được tính công hoặc lương.
                </p>
              </aside>
            ) : null}
            {today?.status === "REJECTED" ? (
              <aside
                className="mt-4 flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-950"
                role="alert"
              >
                <CircleAlert
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-red-800"
                />
                <p>
                  Vị trí đã bị từ chối. Lượt chấm công này không được tính công
                  hoặc lương.
                </p>
              </aside>
            ) : null}
            {today ? (
              <button
                aria-expanded={showLocationEvidence}
                className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-primary-200 bg-white px-3 text-sm font-bold text-primary-800 transition hover:bg-primary-50"
                onClick={() => setShowLocationEvidence((current) => !current)}
                type="button"
              >
                <MapPinned aria-hidden="true" className="size-4" />
                {showLocationEvidence
                  ? "Ẩn bằng chứng vị trí"
                  : "Xem bằng chứng vị trí"}
              </button>
            ) : null}
            {today && showLocationEvidence ? (
              <PersonalAttendanceLocationEvidence
                attendanceId={today.id}
                onClose={() => setShowLocationEvidence(false)}
              />
            ) : null}
            {isCapturingLocation ? (
              <p
                className="mt-3 text-sm font-semibold text-primary-800"
                role="status"
              >
                Đang lấy vị trí GPS từ thiết bị…
              </p>
            ) : null}
            {locationSummary ? (
              <p
                className="mt-3 text-sm font-semibold text-primary-800"
                role="status"
              >
                {locationSummary}
              </p>
            ) : null}
            {notice ? (
              <p
                className="mt-4 text-sm font-semibold text-emerald-800"
                role="status"
              >
                {notice}
              </p>
            ) : null}
            {actionError ? (
              <p
                className="mt-4 text-sm font-semibold text-red-700"
                role="alert"
              >
                {errorMessage(actionError)}
              </p>
            ) : null}
          </section>

          <AttendanceHistory rows={rows} total={attendance.data.meta.total} />
        </div>
      ) : null}
    </section>
  );
}

function AttendanceSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Đang tải chấm công"
      className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]"
    >
      <div className="h-64 animate-pulse rounded-2xl bg-neutral-100" />
      <div className="h-64 animate-pulse rounded-2xl bg-neutral-100" />
    </div>
  );
}

function AttendanceError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
      <CircleAlert aria-hidden="true" className="mx-auto size-8 text-red-700" />
      <h2 className="mt-3 font-bold text-neutral-950">
        Không tải được dữ liệu chấm công
      </h2>
      <p className="mt-1 text-sm text-neutral-700">{errorMessage(error)}</p>
      <button
        className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white"
        onClick={onRetry}
        type="button"
      >
        <RefreshCw aria-hidden="true" className="size-4" /> Thử lại
      </button>
    </div>
  );
}

function TimeTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
        {label}
      </p>
      <p className="mt-2 font-mono text-lg font-bold text-neutral-950">
        {value}
      </p>
    </div>
  );
}

function ActionButton({
  disabled,
  icon: Icon,
  label,
  onClick,
}: {
  disabled: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-6 text-sm font-bold text-neutral-950 shadow-sm transition hover:-translate-y-0.5 hover:bg-emerald-300 active:translate-y-0 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 sm:w-auto"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <Icon aria-hidden="true" className="size-4" /> {label}
    </button>
  );
}

function AttendanceHistory({
  rows,
  total,
}: {
  rows: Attendance[];
  total: number;
}) {
  const [evidenceAttendanceId, setEvidenceAttendanceId] = useState<
    string | null
  >(null);

  return (
    <section
      aria-labelledby="history-title"
      className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5 sm:p-6"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
            20 ngày gần nhất
          </p>
          <h2
            className="mt-2 text-xl font-bold text-neutral-950"
            id="history-title"
          >
            Lịch sử của bạn
          </h2>
        </div>
        <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-neutral-700">
          {total} bản ghi
        </span>
      </div>
      <div className="mt-5 space-y-2">
        {rows.length === 0 ? (
          <p className="rounded-xl border border-dashed border-neutral-300 bg-white p-5 text-center text-sm text-neutral-600">
            Chưa có bản ghi. Hãy bắt đầu ngày làm việc đầu tiên của bạn.
          </p>
        ) : (
          rows.map((item) => {
            const isEvidenceOpen = evidenceAttendanceId === item.id;
            return (
              <article
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3"
                key={item.id}
              >
                <div>
                  <p className="text-sm font-bold text-neutral-950">
                    {formatWorkdayDate(item.workDate)}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    Vào {formatTime(item.checkInAt)} · Ra{" "}
                    {formatTime(item.checkOutAt)}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${statusPresentation[item.status].className}`}
                >
                  {statusPresentation[item.status].label}
                </span>
                <button
                  aria-expanded={isEvidenceOpen}
                  aria-label={`${isEvidenceOpen ? "Ẩn" : "Xem"} bằng chứng vị trí ngày ${evidenceActionDate(item.workDate)}`}
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-primary-200 bg-white px-3 text-xs font-bold text-primary-800 transition hover:bg-primary-50"
                  onClick={() =>
                    setEvidenceAttendanceId((current) =>
                      current === item.id ? null : item.id,
                    )
                  }
                  type="button"
                >
                  <MapPinned aria-hidden="true" className="size-4" />
                  {isEvidenceOpen ? "Ẩn bằng chứng" : "Xem bằng chứng"}
                </button>
                {isEvidenceOpen ? (
                  <div className="w-full">
                    <PersonalAttendanceLocationEvidence
                      attendanceId={item.id}
                      onClose={() => setEvidenceAttendanceId(null)}
                    />
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
