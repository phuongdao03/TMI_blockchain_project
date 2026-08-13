"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, RefreshCw, X } from "lucide-react";
import { useState } from "react";

import { operationsApi } from "@/lib/api/client";
import type { DurableJobSummary } from "@/lib/api/types";

const taskLabels: Record<string, string> = {
  "blockchain.broadcast": "Phát hành chứng thư",
  "blockchain.confirm": "Xác nhận phát hành",
  "blockchain.reconcile": "Đối soát phát hành",
  "payment.reconcile_pending": "Đối soát thanh toán",
};

const statusLabels: Record<DurableJobSummary["status"], string> = {
  QUEUED: "Đang chờ",
  RUNNING: "Đang xử lý",
  SUCCEEDED: "Đã hoàn tất",
  DEAD_LETTERED: "Cần xử lý",
  CANCELLED: "Đã hủy",
};

type PendingAction = {
  job: DurableJobSummary;
  type: "replay" | "cancel";
};

export function JobOperationsWorkspace() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<PendingAction | null>(null);
  const [reason, setReason] = useState("");
  const jobs = useQuery({
    queryKey: ["admin", "operations", "jobs", page],
    queryFn: () => operationsApi.listJobs(page),
  });
  const mutation = useMutation({
    mutationFn: async ({ job, type }: PendingAction) => {
      const input = { expectedVersion: job.version, reason: reason.trim() };
      return type === "replay"
        ? operationsApi.replayJob(job.id, input)
        : operationsApi.cancelJob(job.id, input);
    },
    onSuccess: async () => {
      setAction(null);
      setReason("");
      await queryClient.invalidateQueries({
        queryKey: ["admin", "operations", "jobs"],
      });
    },
  });

  return (
    <section
      className="border-t border-neutral-200 pt-7"
      aria-labelledby="job-queue-title"
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Kiểm soát tác vụ
          </p>
          <h2 className="mt-2 text-xl font-bold" id="job-queue-title">
            Công việc nền gần đây
          </h2>
          <p className="mt-1 text-sm text-neutral-600">
            Theo dõi các bước phát hành và đối soát cần can thiệp.
          </p>
        </div>
        <button
          className="inline-flex min-h-10 items-center gap-2 border border-neutral-300 px-4 text-sm font-bold hover:bg-neutral-50"
          onClick={() => jobs.refetch()}
          type="button"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Làm mới
        </button>
      </div>

      {jobs.isPending ? (
        <p className="mt-6 text-sm text-neutral-600" role="status">
          Đang tải danh sách công việc...
        </p>
      ) : jobs.isError || !jobs.data ? (
        <p className="mt-6 text-sm text-error" role="alert">
          Không thể tải danh sách công việc. Vui lòng thử lại.
        </p>
      ) : jobs.data.data.length === 0 ? (
        <p className="mt-6 border border-dashed border-neutral-300 p-6 text-sm text-neutral-600">
          Chưa có công việc nền nào được ghi nhận.
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto border-y border-neutral-200">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">Công việc</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3">Số lần thử</th>
                <th className="px-4 py-3">Cập nhật</th>
                <th className="px-4 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {jobs.data.data.map((job) => (
                <tr key={job.id}>
                  <td className="px-4 py-4 font-semibold">
                    {taskLabels[job.taskName] ?? "Tác vụ vận hành"}
                    <details className="mt-1 font-normal text-neutral-500">
                      <summary className="cursor-pointer text-xs">
                        Xem chi tiết
                      </summary>
                      <span className="mt-1 block font-mono text-[11px]">
                        {job.taskName}
                      </span>
                    </details>
                  </td>
                  <td className="px-4 py-4">{statusLabels[job.status]}</td>
                  <td className="px-4 py-4 tabular-nums">
                    {job.totalAttempts}/{job.maxAttempts}
                  </td>
                  <td className="px-4 py-4 text-neutral-600">
                    {new Intl.DateTimeFormat("vi-VN", {
                      dateStyle: "short",
                      timeStyle: "short",
                    }).format(new Date(job.updatedAt))}
                  </td>
                  <td className="px-4 py-4 text-right">
                    {job.status === "DEAD_LETTERED" ? (
                      <button
                        className="font-bold text-primary-700"
                        onClick={() => setAction({ job, type: "replay" })}
                        type="button"
                      >
                        Thử lại
                      </button>
                    ) : job.status === "QUEUED" ? (
                      <button
                        className="font-bold text-neutral-700"
                        onClick={() => setAction({ job, type: "cancel" })}
                        type="button"
                      >
                        Hủy công việc
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {jobs.data.meta.total > jobs.data.meta.pageSize ? (
            <nav
              aria-label="Phân trang công việc"
              className="flex items-center justify-between border-t border-neutral-200 px-4 py-3"
            >
              <button
                className="text-sm font-bold disabled:text-neutral-400"
                disabled={page === 1}
                onClick={() => setPage((value) => value - 1)}
                type="button"
              >
                Trang trước
              </button>
              <span className="text-xs text-neutral-600">Trang {page}</span>
              <button
                className="text-sm font-bold disabled:text-neutral-400"
                disabled={
                  page * jobs.data.meta.pageSize >= jobs.data.meta.total
                }
                onClick={() => setPage((value) => value + 1)}
                type="button"
              >
                Trang sau
              </button>
            </nav>
          ) : null}
        </div>
      )}

      {action ? (
        <dialog
          aria-labelledby="job-action-title"
          className="fixed inset-0 z-50 m-auto w-[min(92vw,32rem)] border border-neutral-300 bg-white p-0 shadow-xl"
          open
        >
          <form
            className="p-6"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate(action);
            }}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-primary-700">
                  Yêu cầu xác nhận
                </p>
                <h3 className="mt-2 text-xl font-bold" id="job-action-title">
                  {action.type === "replay"
                    ? "Thử lại công việc"
                    : "Hủy công việc"}
                </h3>
              </div>
              <button
                aria-label="Đóng"
                onClick={() => setAction(null)}
                type="button"
              >
                <X className="size-5" />
              </button>
            </div>
            <label
              className="mt-6 block text-sm font-bold"
              htmlFor="job-action-reason"
            >
              Lý do xử lý
            </label>
            <textarea
              className="mt-2 min-h-28 w-full border border-neutral-300 p-3 text-sm"
              id="job-action-reason"
              maxLength={500}
              minLength={10}
              onChange={(event) => setReason(event.target.value)}
              required
              value={reason}
            />
            {mutation.isError ? (
              <p className="mt-3 flex gap-2 text-sm text-error" role="alert">
                <AlertCircle className="size-4 shrink-0" />
                Không thể cập nhật công việc. Hãy làm mới và thử lại.
              </p>
            ) : null}
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="min-h-10 px-4 text-sm font-bold"
                onClick={() => setAction(null)}
                type="button"
              >
                Quay lại
              </button>
              <button
                className="min-h-10 bg-neutral-950 px-4 text-sm font-bold text-white disabled:opacity-40"
                disabled={reason.trim().length < 10 || mutation.isPending}
                type="submit"
              >
                {action.type === "replay" ? "Xác nhận thử lại" : "Xác nhận hủy"}
              </button>
            </div>
          </form>
        </dialog>
      ) : null}
    </section>
  );
}
