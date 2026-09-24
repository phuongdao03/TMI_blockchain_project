"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  MapPin,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import dynamic from "next/dynamic";

import { ApiError, hrAdminAttendanceApi } from "@/lib/api/client";
import type {
  AdminAttendanceLocationException,
  AttendanceLocationExceptionStatus,
  AttendanceLocationOutcome,
} from "@/lib/api/types";

const AttendanceEvidenceMap = dynamic(
  () =>
    import("./attendance-evidence-map").then(
      (module) => module.AttendanceEvidenceMap,
    ),
  { ssr: false },
);

const outcomeLabels: Record<AttendanceLocationOutcome, string> = {
  ACCEPTED: "Đạt điều kiện",
  OUTSIDE_WORKSITE: "Ngoài bán kính",
  LOW_ACCURACY: "Độ chính xác GPS thấp",
  LOCATION_UNAVAILABLE: "Không lấy được vị trí",
  EXCEPTION_APPROVED: "Ngoại lệ đã duyệt",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value: string, timeZone: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone,
  }).format(new Date(value));
}

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể quyết định lượt chấm công. Vui lòng thử lại.";
}

export function AttendanceLocationExceptionPanel() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [decisionNote, setDecisionNote] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const exceptions = useQuery({
    queryKey: ["hr", "admin-attendance-location-exceptions", "PENDING"],
    queryFn: () =>
      hrAdminAttendanceApi.listLocationExceptions({
        status: "PENDING",
        pageSize: 20,
      }),
  });
  const rows = exceptions.data?.data ?? [];
  const selected =
    rows.find((item) => item.id === selectedId) ?? rows.at(0) ?? null;
  const decision = useMutation({
    mutationFn: ({
      exceptionId,
      status,
      note,
    }: {
      exceptionId: string;
      status: Extract<
        AttendanceLocationExceptionStatus,
        "APPROVED" | "REJECTED"
      >;
      note: string;
    }) =>
      hrAdminAttendanceApi.decideLocationException(exceptionId, {
        status,
        decisionNote: note,
      }),
    onSuccess: (_result, variables) => {
      setDecisionNote("");
      setSelectedId(null);
      setNotice(
        variables.status === "APPROVED"
          ? "Đã duyệt lượt chấm công và ghi audit."
          : "Đã từ chối lượt chấm công và ghi audit.",
      );
      void queryClient.invalidateQueries({
        queryKey: ["hr", "admin-attendance-location-exceptions"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["hr", "admin-attendance"],
      });
    },
  });

  function choose(item: AdminAttendanceLocationException) {
    setSelectedId(item.id);
    setDecisionNote("");
    setValidationError(null);
  }

  function decide(
    status: Extract<AttendanceLocationExceptionStatus, "APPROVED" | "REJECTED">,
  ) {
    const note = decisionNote.trim();
    if (note.length < 2) {
      setValidationError("Nhập lý do gồm ít nhất 2 ký tự.");
      return;
    }
    if (!selected) return;
    setValidationError(null);
    setNotice(null);
    decision.mutate({ exceptionId: selected.id, status, note });
  }

  return (
    <section
      aria-labelledby="location-exception-title"
      className="attendance-exception-panel rounded-2xl border border-amber-200 bg-amber-50/50 p-5 dark:border-amber-900 dark:bg-neutral-950 sm:p-6"
    >
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-amber-800">
            <ShieldCheck aria-hidden="true" className="size-4" /> Xét duyệt bảo
            mật
          </p>
          <h2
            className="mt-2 text-xl font-bold tracking-tight text-neutral-950 dark:text-white"
            id="location-exception-title"
          >
            Vị trí cần xét duyệt
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700 dark:text-neutral-300">
            Chỉ Super Admin xem được bằng chứng GPS chính xác. Duyệt hoặc từ
            chối tại đây để tránh điều chỉnh thủ công làm sai trạng thái chấm
            công.
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-white px-3 py-1.5 text-xs font-bold text-amber-900">
          <CircleAlert aria-hidden="true" className="size-4" />
          {exceptions.data?.meta.total ?? 0} chờ duyệt
        </span>
      </header>

      {notice ? (
        <p
          className="mt-5 text-sm font-semibold text-emerald-800"
          role="status"
        >
          {notice}
        </p>
      ) : null}
      {exceptions.isError ? (
        <div
          className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4"
          role="alert"
        >
          <p className="font-bold text-red-900">
            Không tải được bằng chứng vị trí
          </p>
          <p className="mt-1 text-sm text-red-800">
            {apiMessage(exceptions.error)}
          </p>
          <button
            className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg border border-red-300 bg-white px-3 text-sm font-bold text-red-900"
            onClick={() => void exceptions.refetch()}
            type="button"
          >
            <RefreshCw aria-hidden="true" className="size-4" /> Thử lại
          </button>
        </div>
      ) : null}
      {exceptions.isPending ? (
        <div
          aria-busy="true"
          aria-label="Đang tải các lượt chấm công chờ duyệt vị trí"
          className="mt-5 h-44 animate-pulse rounded-xl bg-amber-100"
        />
      ) : null}
      {!exceptions.isPending && !exceptions.isError && rows.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-amber-300 bg-white p-6 text-center">
          <CheckCircle2
            aria-hidden="true"
            className="mx-auto size-8 text-emerald-700"
          />
          <p className="mt-3 font-bold text-neutral-950">
            Không có lượt nào chờ duyệt
          </p>
          <p className="mt-1 text-sm text-neutral-600">
            Các lượt GPS chưa đạt điều kiện sẽ xuất hiện tại đây.
          </p>
        </div>
      ) : null}
      {selected ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)]">
          <div
            className="space-y-2"
            role="list"
            aria-label="Lượt chấm công chờ duyệt"
          >
            {rows.map((item) => (
              <button
                aria-pressed={item.id === selected.id}
                className={`w-full rounded-xl border p-4 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 ${item.id === selected.id ? "border-amber-400 bg-white shadow-sm dark:bg-neutral-900" : "border-amber-100 bg-amber-50 hover:border-amber-300 hover:bg-white dark:border-neutral-700 dark:bg-neutral-900/60 dark:hover:bg-neutral-900"}`}
                key={item.id}
                onClick={() => choose(item)}
                type="button"
              >
                <span className="flex items-start justify-between gap-3">
                  <span>
                    <span className="block font-bold text-neutral-950 dark:text-white">
                      {item.employeeName}
                    </span>
                    <span className="mt-1 block font-mono text-xs text-neutral-500">
                      {item.employeeCode} · {formatDate(item.workDate)}
                    </span>
                  </span>
                  <CircleAlert
                    aria-hidden="true"
                    className="size-4 shrink-0 text-amber-700"
                  />
                </span>
                <span className="mt-3 block text-sm font-semibold text-amber-900">
                  {outcomeLabels[item.evidence.outcome]}
                </span>
              </button>
            ))}
          </div>
          <EvidenceDecisionForm
            decisionNote={decisionNote}
            error={
              validationError ??
              (decision.error ? apiMessage(decision.error) : null)
            }
            isSaving={decision.isPending}
            item={selected}
            onDecisionNoteChange={(value) => {
              setDecisionNote(value);
              setValidationError(null);
            }}
            onDecide={decide}
          />
        </div>
      ) : null}
    </section>
  );
}

function EvidenceDecisionForm({
  decisionNote,
  error,
  isSaving,
  item,
  onDecisionNoteChange,
  onDecide,
}: {
  decisionNote: string;
  error: string | null;
  isSaving: boolean;
  item: AdminAttendanceLocationException;
  onDecisionNoteChange: (value: string) => void;
  onDecide: (
    status: Extract<AttendanceLocationExceptionStatus, "APPROVED" | "REJECTED">,
  ) => void;
}) {
  const { evidence } = item;
  const metrics = [
    ["Điểm chấm công", `${evidence.worksiteName} · ${evidence.worksiteCode}`],
    [
      "Độ chính xác",
      `${evidence.accuracyMeters} m / tối đa ${evidence.maxAccuracyMeters} m`,
    ],
    [
      "Khoảng cách",
      `${evidence.distanceMeters} m / bán kính ${evidence.permittedRadiusMeters} m`,
    ],
    ["Múi giờ địa điểm làm việc", evidence.effectiveTimezone],
  ];

  return (
    <article className="rounded-xl border border-amber-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
            Bằng chứng một lần
          </p>
          <h3 className="mt-1 text-lg font-bold text-neutral-950 dark:text-white">
            {item.employeeName} · {formatDate(item.workDate)}
          </h3>
        </div>
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900">
          <MapPin aria-hidden="true" className="size-3.5" />
          {outcomeLabels[evidence.outcome]}
        </span>
      </div>
      {evidence.latitude !== null && evidence.longitude !== null ? (
        <div className="mt-5">
          <AttendanceEvidenceMap evidence={[evidence]} />
        </div>
      ) : null}
      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        {metrics.map(([label, value]) => (
          <div
            className="rounded-lg bg-neutral-50 p-3 dark:bg-neutral-800"
            key={label}
          >
            <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
              {label}
            </dt>
            <dd className="mt-1 break-words text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 flex items-start gap-2 text-sm leading-6 text-neutral-700 dark:text-neutral-300">
        <Clock3
          aria-hidden="true"
          className="mt-1 size-4 shrink-0 text-neutral-500"
        />
        <span>
          {evidence.eventType === "CHECK_IN" ? "Chấm công vào" : "Chấm công ra"}{" "}
          lúc{" "}
          {formatDateTime(
            evidence.clientCapturedAt,
            evidence.effectiveTimezone,
          )}
          . Dữ liệu máy chủ nhận lúc{" "}
          {formatDateTime(evidence.receivedAt, "UTC")} UTC.
        </span>
      </p>
      <label
        className="mt-5 block text-sm font-bold text-neutral-800 dark:text-neutral-100"
        htmlFor="location-decision-note"
      >
        Lý do quyết định
        <textarea
          className="mt-2 min-h-24 w-full rounded-xl border border-neutral-300 bg-white px-3 py-3 text-sm text-neutral-950 outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-100 dark:border-neutral-700 dark:bg-neutral-800 dark:text-white"
          id="location-decision-note"
          maxLength={2000}
          onChange={(event) => onDecisionNoteChange(event.target.value)}
          placeholder="Ví dụ: Đã xác minh nhân viên làm việc tại địa điểm được phê duyệt."
          value={decisionNote}
        />
      </label>
      {error ? (
        <p className="mt-3 text-sm font-semibold text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSaving}
          onClick={() => onDecide("APPROVED")}
          type="button"
        >
          <CheckCircle2 aria-hidden="true" className="size-4" /> Duyệt vị trí
        </button>
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-red-300 bg-red-50 px-4 text-sm font-bold text-red-900 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSaving}
          onClick={() => onDecide("REJECTED")}
          type="button"
        >
          <XCircle aria-hidden="true" className="size-4" /> Từ chối vị trí
        </button>
      </div>
    </article>
  );
}
