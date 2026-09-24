"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CalendarRange,
  CheckCircle2,
  CircleAlert,
  ClipboardPenLine,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, hrSelfApi } from "@/lib/api/client";
import type { LeaveRequest, LeaveRequestStatus } from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

const statusLabels: Record<LeaveRequestStatus, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  CANCELLED: "Đã hủy",
};

const statusStyle: Record<LeaveRequestStatus, string> = {
  PENDING: "bg-amber-50 text-amber-800 ring-amber-200",
  APPROVED: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  REJECTED: "bg-red-50 text-red-800 ring-red-200",
  CANCELLED: "bg-neutral-100 text-neutral-700 ring-neutral-200",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatRange(startDate: string, endDate: string) {
  if (startDate === endDate) return formatDate(startDate);
  return `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể cập nhật đơn nghỉ. Vui lòng thử lại.";
}

export function LeaveWorkspace() {
  const queryClient = useQueryClient();
  const [leaveType, setLeaveType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const leaveRequests = useQuery({
    queryKey: ["hr", "self", "leave-requests"],
    queryFn: () => hrSelfApi.listLeaveRequests({ pageSize: 20 }),
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: ["hr", "self", "leave-requests"],
    });
  const createRequest = useMutation({
    mutationFn: (input: {
      leaveType: string;
      startDate: string;
      endDate: string;
      reason: string;
    }) => hrSelfApi.createLeaveRequest(input),
    onSuccess: () => {
      setLeaveType("");
      setStartDate("");
      setEndDate("");
      setReason("");
      setNotice("Đơn nghỉ đã được gửi và đang chờ duyệt.");
      void refresh();
    },
  });
  const cancelRequest = useMutation({
    mutationFn: hrSelfApi.cancelLeaveRequest,
    onSuccess: () => {
      setNotice("Đơn nghỉ đã được hủy.");
      void refresh();
    },
  });
  const rows = leaveRequests.data?.data ?? [];

  function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedType = leaveType.trim();
    const trimmedReason = reason.trim();
    if (!trimmedType || !startDate || !endDate || !trimmedReason) {
      setFormError("Hãy điền đủ loại nghỉ, thời gian và lý do.");
      return;
    }
    if (endDate < startDate) {
      setFormError("Ngày kết thúc không thể trước ngày bắt đầu.");
      return;
    }
    setFormError(null);
    createRequest.mutate({
      leaveType: trimmedType,
      startDate,
      endDate,
      reason: trimmedReason,
    });
  }

  function cancel(item: LeaveRequest) {
    if (
      window.confirm(
        "Hủy đơn nghỉ này? Đơn đang chờ duyệt sẽ được chuyển sang trạng thái đã hủy.",
      )
    ) {
      cancelRequest.mutate(item.id);
    }
  }

  return (
    <section
      aria-labelledby="leave-title"
      className="mx-auto max-w-6xl space-y-6 pb-12"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.2),transparent_65%)]" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <CalendarDays aria-hidden="true" className="size-4" /> Nhân sự cá
              nhân
            </p>
            <h1
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
              id="leave-title"
            >
              Nghỉ phép
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Gửi đơn và theo dõi kết quả duyệt tại một nơi. Số dư, quy đổi và
              quy tắc chồng lấp sẽ chỉ được áp dụng khi chính sách nội bộ được
              xác nhận.
            </p>
          </div>
          <p className="inline-flex items-center gap-2 self-start rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-100 sm:self-auto">
            <CalendarRange
              aria-hidden="true"
              className="size-4 text-emerald-300"
            />
            Theo ngày trọn vẹn
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <form
          className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6"
          onSubmit={submitRequest}
        >
          <div className="flex items-start gap-3">
            <span className="rounded-xl bg-emerald-50 p-2.5 text-emerald-800">
              <ClipboardPenLine aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
                Tạo yêu cầu
              </p>
              <h2 className="mt-1 text-xl font-bold text-neutral-950">
                Đơn nghỉ mới
              </h2>
            </div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-bold text-neutral-800 sm:col-span-2">
              Loại nghỉ
              <input
                className={fieldClass}
                maxLength={64}
                onChange={(event) => setLeaveType(event.target.value)}
                placeholder="Ví dụ: Nghỉ phép năm"
                value={leaveType}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Từ ngày
              <input
                className={fieldClass}
                onChange={(event) => setStartDate(event.target.value)}
                type="date"
                value={startDate}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Đến ngày
              <input
                className={fieldClass}
                onChange={(event) => setEndDate(event.target.value)}
                type="date"
                value={endDate}
              />
            </label>
            <label className="text-sm font-bold text-neutral-800 sm:col-span-2">
              Lý do
              <textarea
                className={`${fieldClass} min-h-28 py-3`}
                maxLength={2000}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Mô tả ngắn gọn để người duyệt có đủ bối cảnh"
                value={reason}
              />
            </label>
          </div>
          {formError || createRequest.error ? (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              {formError ?? apiMessage(createRequest.error)}
            </p>
          ) : null}
          <button
            className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-emerald-300 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
            disabled={createRequest.isPending}
            type="submit"
          >
            <ClipboardPenLine aria-hidden="true" className="size-4" />
            {createRequest.isPending ? "Đang gửi..." : "Gửi đơn nghỉ"}
          </button>
        </form>

        <LeaveRequestList
          cancelError={cancelRequest.error}
          isCancelling={cancelRequest.isPending}
          isError={leaveRequests.isError}
          isLoading={leaveRequests.isPending}
          notice={notice}
          onCancel={cancel}
          onRetry={() => void leaveRequests.refetch()}
          requests={rows}
          total={leaveRequests.data?.meta.total ?? 0}
        />
      </div>
    </section>
  );
}

function LeaveRequestList({
  cancelError,
  isCancelling,
  isError,
  isLoading,
  notice,
  onCancel,
  onRetry,
  requests,
  total,
}: {
  cancelError: unknown;
  isCancelling: boolean;
  isError: boolean;
  isLoading: boolean;
  notice: string | null;
  onCancel: (item: LeaveRequest) => void;
  onRetry: () => void;
  requests: LeaveRequest[];
  total: number;
}) {
  return (
    <section
      aria-labelledby="leave-history-title"
      className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
            Lịch sử gần đây
          </p>
          <h2
            className="mt-1 text-xl font-bold text-neutral-950"
            id="leave-history-title"
          >
            Đơn của bạn
          </h2>
        </div>
        <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-neutral-700 ring-1 ring-neutral-200">
          {total} đơn
        </span>
      </div>
      {notice ? (
        <p
          className="mt-4 flex items-center gap-2 text-sm font-semibold text-emerald-800"
          role="status"
        >
          <CheckCircle2 aria-hidden="true" className="size-4" /> {notice}
        </p>
      ) : null}
      {cancelError ? (
        <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
          {apiMessage(cancelError)}
        </p>
      ) : null}
      {isLoading ? (
        <div
          aria-busy="true"
          aria-label="Đang tải đơn nghỉ"
          className="mt-5 space-y-3"
        >
          <div className="h-24 animate-pulse rounded-xl bg-white" />
          <div className="h-24 animate-pulse rounded-xl bg-white" />
        </div>
      ) : null}
      {isError ? (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-5 text-center">
          <CircleAlert
            aria-hidden="true"
            className="mx-auto size-7 text-red-700"
          />
          <p className="mt-2 font-bold text-neutral-950">
            Không tải được đơn nghỉ
          </p>
          <button
            className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white"
            onClick={onRetry}
            type="button"
          >
            <RefreshCw aria-hidden="true" className="size-4" /> Thử lại
          </button>
        </div>
      ) : null}
      {!isLoading && !isError && requests.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-neutral-300 bg-white p-8 text-center">
          <CalendarRange
            aria-hidden="true"
            className="mx-auto size-9 text-neutral-400"
          />
          <p className="mt-3 font-bold text-neutral-950">
            Chưa có đơn nghỉ nào
          </p>
          <p className="mt-1 text-sm text-neutral-600">
            Đơn mới sẽ xuất hiện ở đây.
          </p>
        </div>
      ) : null}
      <div className="mt-5 space-y-3">
        {requests.map((item) => (
          <article
            className="rounded-xl border border-neutral-200 bg-white p-4"
            key={item.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-neutral-950">{item.leaveType}</p>
                <p className="mt-1 text-sm font-semibold text-neutral-700">
                  {formatRange(item.startDate, item.endDate)}
                </p>
              </div>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${statusStyle[item.status]}`}
              >
                {statusLabels[item.status]}
              </span>
            </div>
            <p className="mt-3 line-clamp-2 text-sm leading-5 text-neutral-600">
              {item.reason}
            </p>
            {item.decisionNote ? (
              <p className="mt-3 border-l-2 border-neutral-200 pl-3 text-sm text-neutral-700">
                Phản hồi: {item.decisionNote}
              </p>
            ) : null}
            {item.status === "PENDING" ? (
              <button
                className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 transition hover:bg-neutral-50 disabled:opacity-60"
                disabled={isCancelling}
                onClick={() => onCancel(item)}
                type="button"
              >
                <XCircle aria-hidden="true" className="size-4" />
                {isCancelling ? "Đang hủy..." : "Hủy đơn"}
              </button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
