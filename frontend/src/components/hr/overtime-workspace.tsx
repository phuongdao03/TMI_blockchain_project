"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Clock3, RefreshCw, Send, XCircle } from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, hrSelfApi } from "@/lib/api/client";
import type { OvertimeRequest, OvertimeRequestStatus } from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

const labels: Record<OvertimeRequestStatus, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  CANCELLED: "Đã hủy",
};

const tones: Record<OvertimeRequestStatus, string> = {
  PENDING: "bg-amber-50 text-amber-800",
  APPROVED: "bg-emerald-50 text-emerald-800",
  REJECTED: "bg-red-50 text-red-800",
  CANCELLED: "bg-neutral-100 text-neutral-700",
};

function displayTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể cập nhật yêu cầu tăng ca. Vui lòng thử lại.";
}

export function OvertimeWorkspace() {
  const queryClient = useQueryClient();
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const overtime = useQuery({
    queryKey: ["hr", "self", "overtime-requests"],
    queryFn: () => hrSelfApi.listOvertimeRequests({ pageSize: 20 }),
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: ["hr", "self", "overtime-requests"],
    });
  const create = useMutation({
    mutationFn: (input: { startAt: string; endAt: string; reason: string }) =>
      hrSelfApi.createOvertimeRequest(input),
    onSuccess: () => {
      setStartAt("");
      setEndAt("");
      setReason("");
      void refresh();
    },
  });
  const cancel = useMutation({
    mutationFn: hrSelfApi.cancelOvertimeRequest,
    onSuccess: () => void refresh(),
  });
  const rows = overtime.data?.data ?? [];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!startAt || !endAt || !reason.trim()) {
      setFormError("Hãy điền đủ khoảng thời gian và lý do tăng ca.");
      return;
    }
    const start = new Date(startAt);
    const end = new Date(endAt);
    if (end <= start) {
      setFormError("Thời điểm kết thúc phải sau thời điểm bắt đầu.");
      return;
    }
    setFormError(null);
    create.mutate({
      startAt: start.toISOString(),
      endAt: end.toISOString(),
      reason: reason.trim(),
    });
  }

  return (
    <section
      aria-labelledby="overtime-title"
      className="mx-auto max-w-6xl space-y-6 pb-12"
    >
      <header className="rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
          <Clock3 className="size-4" /> Nhân sự cá nhân
        </p>
        <h1
          className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
          id="overtime-title"
        >
          Đăng ký tăng ca
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
          Gửi khoảng thời gian dự kiến để được duyệt. Hệ thống chưa tự làm tròn
          giờ hoặc tính mức chi trả.
        </p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <form
          className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6"
          onSubmit={submit}
        >
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
            Yêu cầu mới
          </p>
          <h2 className="mt-1 text-xl font-bold text-neutral-950">
            Thời gian dự kiến
          </h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Nhập giờ theo múi giờ trên thiết bị của bạn; hệ thống lưu thời điểm
            có kèm múi giờ để người duyệt đối chiếu nhất quán.
          </p>
          <label className="mt-5 block text-sm font-bold text-neutral-800">
            Bắt đầu
            <input
              className={fieldClass}
              onChange={(event) => setStartAt(event.target.value)}
              type="datetime-local"
              value={startAt}
            />
          </label>
          <label className="mt-4 block text-sm font-bold text-neutral-800">
            Kết thúc
            <input
              className={fieldClass}
              onChange={(event) => setEndAt(event.target.value)}
              type="datetime-local"
              value={endAt}
            />
          </label>
          <label className="mt-4 block text-sm font-bold text-neutral-800">
            Lý do tăng ca
            <textarea
              className={`${fieldClass} min-h-28 py-3`}
              maxLength={2000}
              onChange={(event) => setReason(event.target.value)}
              value={reason}
            />
          </label>
          {formError || create.error ? (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              {formError ?? apiMessage(create.error)}
            </p>
          ) : null}
          <button
            className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-400 px-5 text-sm font-bold text-neutral-950 disabled:opacity-60"
            disabled={create.isPending}
            type="submit"
          >
            <Send className="size-4" />
            {create.isPending ? "Đang gửi..." : "Gửi yêu cầu tăng ca"}
          </button>
        </form>
        <section
          aria-labelledby="overtime-history-title"
          className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5 sm:p-6"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
                Lịch sử gần đây
              </p>
              <h2
                className="mt-1 text-xl font-bold text-neutral-950"
                id="overtime-history-title"
              >
                Yêu cầu của bạn
              </h2>
            </div>
            <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-neutral-700">
              {overtime.data?.meta.total ?? 0} yêu cầu
            </span>
          </div>
          {overtime.isPending ? (
            <div
              aria-busy="true"
              aria-label="Đang tải yêu cầu tăng ca"
              className="mt-5 h-28 animate-pulse rounded-xl bg-white"
            />
          ) : null}
          {overtime.isError ? (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-5 text-center">
              <CircleAlert className="mx-auto size-7 text-red-700" />
              <p className="mt-2 font-bold">Không tải được yêu cầu tăng ca</p>
              <button
                className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary-700"
                onClick={() => void overtime.refetch()}
                type="button"
              >
                <RefreshCw className="size-4" /> Thử lại
              </button>
            </div>
          ) : null}
          {!overtime.isPending && !overtime.isError && rows.length === 0 ? (
            <p className="mt-5 rounded-xl border border-dashed border-neutral-300 bg-white p-8 text-center text-sm text-neutral-600">
              Chưa có yêu cầu tăng ca nào.
            </p>
          ) : null}
          <div className="mt-5 space-y-3">
            {rows.map((item) => (
              <OvertimeCard
                item={item}
                isCancelling={cancel.isPending}
                key={item.id}
                onCancel={() =>
                  window.confirm("Hủy yêu cầu tăng ca này?") &&
                  cancel.mutate(item.id)
                }
              />
            ))}
          </div>
          {cancel.error ? (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              {apiMessage(cancel.error)}
            </p>
          ) : null}
        </section>
      </div>
    </section>
  );
}

function OvertimeCard({
  item,
  isCancelling,
  onCancel,
}: {
  item: OvertimeRequest;
  isCancelling: boolean;
  onCancel: () => void;
}) {
  return (
    <article className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="font-bold text-neutral-950">
          {displayTime(item.startAt)} – {displayTime(item.endAt)}
        </p>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-bold ${tones[item.status]}`}
        >
          {labels[item.status]}
        </span>
      </div>
      <p className="mt-3 text-sm text-neutral-600">{item.reason}</p>
      {item.decisionNote ? (
        <p className="mt-3 border-l-2 border-neutral-200 pl-3 text-sm text-neutral-700">
          Phản hồi: {item.decisionNote}
        </p>
      ) : null}
      {item.status === "PENDING" ? (
        <button
          className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 disabled:opacity-60"
          disabled={isCancelling}
          onClick={onCancel}
          type="button"
        >
          <XCircle className="size-4" /> Hủy yêu cầu
        </button>
      ) : null}
    </article>
  );
}
