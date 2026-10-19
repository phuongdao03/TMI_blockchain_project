"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, ClipboardList } from "lucide-react";

import { myTaskApi } from "@/lib/api/client";
import type { WorkTask } from "@/lib/api/types";

const statusLabels: Record<WorkTask["status"], string> = {
  TODO: "Chưa bắt đầu",
  IN_PROGRESS: "Đang thực hiện",
  DONE: "Hoàn thành",
  CANCELLED: "Đã hủy",
};

function formatDueDate(value: string | null) {
  if (!value) return "Chưa đặt hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function MyTasksWorkspace() {
  const queryClient = useQueryClient();
  const tasks = useQuery({
    queryKey: ["my-tasks"],
    queryFn: () => myTaskApi.list(),
  });
  const updateStatus = useMutation({
    mutationFn: ({
      taskId,
      status,
    }: {
      taskId: string;
      status: "IN_PROGRESS" | "DONE";
    }) => myTaskApi.update(taskId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-tasks"] }),
  });
  const rows = tasks.data?.data ?? [];
  const openCount = rows.filter(
    (task) => task.status === "TODO" || task.status === "IN_PROGRESS",
  ).length;

  return (
    <section
      aria-labelledby="my-tasks-title"
      className="mx-auto w-full max-w-5xl space-y-5 pb-12"
    >
      <header className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 text-[var(--theme-text)] sm:p-7">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--theme-accent)]">
          <ClipboardList aria-hidden="true" className="size-4" /> Công việc của
          tôi
        </p>
        <h1
          className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl"
          id="my-tasks-title"
        >
          Việc được giao
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
          Xem các việc đang cần bạn thực hiện và hạn hoàn thành.
        </p>
        {!tasks.isPending && !tasks.isError ? (
          <p className="mt-4 inline-flex items-center gap-2 rounded-full bg-primary-50 px-3 py-1.5 text-sm font-semibold text-primary-900 dark:bg-primary-950/40 dark:text-primary-100">
            <CalendarClock aria-hidden="true" className="size-4" />
            {openCount} việc cần xử lý
          </p>
        ) : null}
      </header>

      <section
        aria-label="Danh sách việc được giao"
        className="overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]"
      >
        {tasks.isPending ? (
          <p className="p-5 text-sm text-[var(--theme-muted)]" role="status">
            Đang tải danh sách việc…
          </p>
        ) : null}
        {tasks.isError ? (
          <p className="p-5 text-sm text-red-700" role="alert">
            Chưa tải được danh sách việc. Hãy thử tải lại trang.
          </p>
        ) : null}
        {updateStatus.isError ? (
          <p
            className="border-b border-[var(--theme-border)] p-4 text-sm text-red-700"
            role="alert"
          >
            Chưa cập nhật được trạng thái. Hãy tải lại danh sách và thử lại.
          </p>
        ) : null}
        {!tasks.isPending && !tasks.isError && rows.length === 0 ? (
          <div className="px-5 py-10 text-center sm:py-12">
            <CheckCircle2
              aria-hidden="true"
              className="mx-auto size-8 text-emerald-700"
            />
            <p className="mt-3 text-sm font-semibold text-[var(--theme-text)]">
              Hiện chưa có việc nào được giao cho bạn.
            </p>
          </div>
        ) : null}
        {rows.length > 0 ? (
          <ul className="divide-y divide-[var(--theme-border)]">
            {rows.map((task) => (
              <li
                className="flex min-w-0 flex-col gap-3 p-4 sm:p-5"
                key={task.id}
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <h2 className="min-w-0 text-base font-semibold leading-6 text-[var(--theme-text)]">
                    {task.title}
                  </h2>
                  <span className="shrink-0 rounded-full bg-primary-50 px-2.5 py-1 text-xs font-semibold text-primary-900 dark:bg-primary-950/40 dark:text-primary-100">
                    {statusLabels[task.status]}
                  </span>
                </div>
                {task.description ? (
                  <p className="text-sm leading-5 text-[var(--theme-muted)]">
                    {task.description}
                  </p>
                ) : null}
                <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                  <p className="flex items-center gap-1.5 text-xs text-[var(--theme-muted)]">
                    <CalendarClock aria-hidden="true" className="size-3.5" />
                    Hạn hoàn thành: {formatDueDate(task.dueAt)}
                  </p>
                  {task.status === "TODO" ? (
                    <button
                      className="min-h-10 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-semibold text-[var(--theme-accent-contrast)] disabled:opacity-60"
                      disabled={updateStatus.isPending}
                      onClick={() =>
                        updateStatus.mutate({
                          taskId: task.id,
                          status: "IN_PROGRESS",
                        })
                      }
                      type="button"
                    >
                      Bắt đầu
                    </button>
                  ) : task.status === "IN_PROGRESS" ? (
                    <button
                      className="min-h-10 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-semibold text-[var(--theme-accent-contrast)] disabled:opacity-60"
                      disabled={updateStatus.isPending}
                      onClick={() =>
                        updateStatus.mutate({ taskId: task.id, status: "DONE" })
                      }
                      type="button"
                    >
                      Đánh dấu hoàn thành
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </section>
  );
}
