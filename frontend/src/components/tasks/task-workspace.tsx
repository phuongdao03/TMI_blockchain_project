"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownUp,
  CheckCircle2,
  CircleAlert,
  ClipboardList,
  Plus,
  Search,
  SquareArrowOutUpRight,
  XCircle,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, taskAdminApi } from "@/lib/api/client";
import { HrReportDownload } from "@/components/hr/hr-report-download";
import type {
  WorkTask,
  WorkTaskPriority,
  WorkTaskStatus,
} from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

const statusLabels: Record<WorkTaskStatus, string> = {
  TODO: "Chưa bắt đầu",
  IN_PROGRESS: "Đang thực hiện",
  DONE: "Hoàn thành",
  CANCELLED: "Đã hủy",
};

const priorityLabels: Record<WorkTaskPriority, string> = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Khẩn cấp",
};

const statusTones: Record<WorkTaskStatus, string> = {
  TODO: "bg-neutral-100 text-neutral-700",
  IN_PROGRESS: "bg-sky-50 text-sky-800",
  DONE: "bg-emerald-50 text-emerald-800",
  CANCELLED: "bg-red-50 text-red-800",
};

const priorityTones: Record<WorkTaskPriority, string> = {
  LOW: "text-neutral-600",
  MEDIUM: "text-sky-700",
  HIGH: "text-amber-700",
  CRITICAL: "text-red-700",
};

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể cập nhật công việc. Vui lòng thử lại.";
}

function formatDateTime(value: string | null) {
  if (!value) return "Chưa đặt hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function TaskWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<WorkTaskStatus | "">("");
  const [priority, setPriority] = useState<WorkTaskPriority | "">("");
  const [sortBy, setSortBy] = useState<"createdAt" | "dueAt">("createdAt");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const tasks = useQuery({
    queryKey: ["tasks", search, status, priority, sortBy, sortDirection, page],
    queryFn: () =>
      taskAdminApi.list({
        search: search || undefined,
        status: status || undefined,
        priority: priority || undefined,
        sortBy,
        sortDirection,
        page,
        pageSize: 20,
      }),
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const create = useMutation({
    mutationFn: (input: {
      title: string;
      description: string | null;
      dueAt: string | null;
    }) => taskAdminApi.create(input),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      setDueAt("");
      setFormError(null);
      setPage(1);
      void refresh();
    },
  });
  const transition = useMutation({
    mutationFn: ({
      taskId,
      nextStatus,
    }: {
      taskId: string;
      nextStatus: WorkTaskStatus;
    }) => taskAdminApi.update(taskId, { status: nextStatus }),
    onSuccess: () => void refresh(),
  });
  const rows = tasks.data?.data ?? [];
  const total = tasks.data?.meta.total ?? 0;

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      setFormError("Tên công việc là bắt buộc.");
      return;
    }
    setFormError(null);
    create.mutate({
      title: title.trim(),
      description: description.trim() || null,
      dueAt: dueAt ? new Date(dueAt).toISOString() : null,
    });
  }

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setPage(1);
  }

  function transitionTask(task: WorkTask, nextStatus: WorkTaskStatus) {
    if (
      window.confirm(
        `Xác nhận chuyển “${task.title}” sang ${statusLabels[nextStatus].toLowerCase()}? Thay đổi sẽ được ghi vào audit log.`,
      )
    ) {
      transition.mutate({ taskId: task.id, nextStatus });
    }
  }

  return (
    <section
      aria-labelledby="tasks-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <ClipboardList aria-hidden="true" className="size-4" /> Điều hành
              công việc
            </p>
            <h1
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
              id="tasks-title"
            >
              Công việc trọng tâm
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Tạo, theo dõi và chuyển trạng thái công việc trong một không gian
              rõ ràng, có kiểm soát và audit.
            </p>
          </div>
          <span className="rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-100">
            {total} công việc
          </span>
        </div>
      </header>

      <HrReportDownload
        download={() =>
          taskAdminApi.exportXlsx({
            search: search || undefined,
            status: status || undefined,
            priority: priority || undefined,
          })
        }
        errorMessage="Không thể tải báo cáo công việc."
        filename="hr-tasks.xlsx"
      />

      <div className="grid gap-6 xl:grid-cols-[21rem_1fr]">
        <form
          className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6"
          onSubmit={submitCreate}
        >
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
            Công việc mới
          </p>
          <h2 className="mt-1 text-xl font-bold text-neutral-950">
            Tạo rõ mục tiêu
          </h2>
          <label className="mt-5 block text-sm font-bold text-neutral-800">
            Tên công việc
            <input
              aria-label="Tên công việc"
              className={fieldClass}
              maxLength={240}
              onChange={(event) => setTitle(event.target.value)}
              value={title}
            />
          </label>
          <label className="mt-4 block text-sm font-bold text-neutral-800">
            Mô tả{" "}
            <span className="font-normal text-neutral-500">
              (không bắt buộc)
            </span>
            <textarea
              className={`${fieldClass} min-h-24 py-3`}
              maxLength={10000}
              onChange={(event) => setDescription(event.target.value)}
              value={description}
            />
          </label>
          <label className="mt-4 block text-sm font-bold text-neutral-800">
            Hạn hoàn thành{" "}
            <span className="font-normal text-neutral-500">
              (không bắt buộc)
            </span>
            <input
              className={fieldClass}
              onChange={(event) => setDueAt(event.target.value)}
              type="datetime-local"
              value={dueAt}
            />
          </label>
          {formError || create.error ? (
            <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
              {formError ?? apiMessage(create.error)}
            </p>
          ) : null}
          <button
            className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-emerald-300 disabled:opacity-60"
            disabled={create.isPending}
            type="submit"
          >
            <Plus aria-hidden="true" className="size-4" />{" "}
            {create.isPending ? "Đang tạo..." : "Tạo công việc"}
          </button>
        </form>

        <div className="space-y-4">
          <form
            className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-2 xl:grid-cols-[1.2fr_10rem_10rem_10rem_auto]"
            onSubmit={submitFilters}
          >
            <label className="text-sm font-bold text-neutral-800">
              Tìm công việc
              <span className="relative mt-2 block">
                <Search
                  aria-hidden="true"
                  className="absolute left-3 top-3.5 size-4 text-neutral-400"
                />
                <input
                  className={`${fieldClass} mt-0 pl-10`}
                  onChange={(event) => setSearchDraft(event.target.value)}
                  placeholder="Tên công việc"
                  value={searchDraft}
                />
              </span>
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Trạng thái
              <select
                className={fieldClass}
                onChange={(event) => {
                  setStatus(event.target.value as WorkTaskStatus | "");
                  setPage(1);
                }}
                value={status}
              >
                <option value="">Tất cả</option>
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Ưu tiên
              <select
                className={fieldClass}
                onChange={(event) => {
                  setPriority(event.target.value as WorkTaskPriority | "");
                  setPage(1);
                }}
                value={priority}
              >
                <option value="">Tất cả</option>
                {Object.entries(priorityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold text-neutral-800">
              Sắp xếp
              <select
                className={fieldClass}
                onChange={(event) => {
                  setSortBy(event.target.value as "createdAt" | "dueAt");
                  setPage(1);
                }}
                value={sortBy}
              >
                <option value="createdAt">Ngày tạo</option>
                <option value="dueAt">Hạn hoàn thành</option>
              </select>
            </label>
            <button
              className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-neutral-800"
              type="submit"
            >
              Áp dụng
            </button>
          </form>

          <section
            aria-labelledby="task-list-title"
            className="overflow-hidden rounded-2xl border border-neutral-200 bg-white"
          >
            <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-5 py-3">
              <h2
                className="text-sm font-bold text-neutral-950"
                id="task-list-title"
              >
                Danh sách công việc
              </h2>
              <button
                className="inline-flex items-center gap-2 text-xs font-bold text-neutral-700"
                onClick={() => {
                  setSortDirection((value) =>
                    value === "asc" ? "desc" : "asc",
                  );
                  setPage(1);
                }}
                type="button"
              >
                <ArrowDownUp aria-hidden="true" className="size-3.5" />
                {sortDirection === "asc" ? "Tăng dần" : "Giảm dần"}
              </button>
            </div>
            {tasks.isPending ? (
              <div
                aria-busy="true"
                aria-label="Đang tải công việc"
                className="m-5 h-44 animate-pulse rounded-xl bg-neutral-100"
              />
            ) : null}
            {tasks.isError ? (
              <div className="p-10 text-center">
                <CircleAlert
                  aria-hidden="true"
                  className="mx-auto size-8 text-red-700"
                />
                <p className="mt-3 font-bold text-neutral-950">
                  Không tải được danh sách công việc
                </p>
                <button
                  className="mt-3 text-sm font-bold text-primary-700"
                  onClick={() => void tasks.refetch()}
                  type="button"
                >
                  Thử lại
                </button>
              </div>
            ) : null}
            {transition.isError ? (
              <p
                className="border-b border-red-100 bg-red-50 px-5 py-3 text-sm font-semibold text-red-800"
                role="alert"
              >
                {apiMessage(transition.error)}
              </p>
            ) : null}
            {!tasks.isPending && !tasks.isError && rows.length === 0 ? (
              <div className="p-10 text-center">
                <ClipboardList
                  aria-hidden="true"
                  className="mx-auto size-9 text-neutral-400"
                />
                <p className="mt-3 font-bold text-neutral-950">
                  Chưa có công việc phù hợp
                </p>
                <p className="mt-1 text-sm text-neutral-600">
                  Tạo việc mới hoặc thay đổi bộ lọc để tiếp tục.
                </p>
              </div>
            ) : null}
            <div className="divide-y divide-neutral-100">
              {rows.map((task) => (
                <TaskRow
                  isSaving={transition.isPending}
                  key={task.id}
                  onTransition={transitionTask}
                  task={task}
                />
              ))}
            </div>
            {total > 20 ? (
              <div className="flex items-center justify-between border-t border-neutral-200 px-5 py-3 text-sm">
                <button
                  className="font-bold text-primary-700 disabled:text-neutral-400"
                  disabled={page === 1}
                  onClick={() => setPage((value) => value - 1)}
                  type="button"
                >
                  Trang trước
                </button>
                <span className="text-neutral-600">Trang {page}</span>
                <button
                  className="font-bold text-primary-700 disabled:text-neutral-400"
                  disabled={page * 20 >= total}
                  onClick={() => setPage((value) => value + 1)}
                  type="button"
                >
                  Trang sau
                </button>
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </section>
  );
}

function TaskRow({
  task,
  onTransition,
  isSaving,
}: {
  task: WorkTask;
  onTransition: (task: WorkTask, nextStatus: WorkTaskStatus) => void;
  isSaving: boolean;
}) {
  const actions: Partial<
    Record<
      WorkTaskStatus,
      { label: string; status: WorkTaskStatus; icon: typeof CheckCircle2 }
    >
  > = {
    TODO: {
      label: "Bắt đầu",
      status: "IN_PROGRESS",
      icon: SquareArrowOutUpRight,
    },
    IN_PROGRESS: { label: "Hoàn thành", status: "DONE", icon: CheckCircle2 },
  };
  const action = actions[task.status];
  return (
    <article className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate font-bold text-neutral-950">{task.title}</h3>
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusTones[task.status]}`}
          >
            {statusLabels[task.status]}
          </span>
        </div>
        {task.description ? (
          <p className="mt-2 line-clamp-2 text-sm leading-5 text-neutral-600">
            {task.description}
          </p>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
          <span className={priorityTones[task.priority]}>
            Ưu tiên: {priorityLabels[task.priority]}
          </span>
          <span className="text-neutral-500">
            Hạn: {formatDateTime(task.dueAt)}
          </span>
        </div>
      </div>
      <div className="flex shrink-0 gap-2">
        {action ? (
          <button
            className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-neutral-950 px-3 text-xs font-bold text-white disabled:opacity-60"
            disabled={isSaving}
            onClick={() => onTransition(task, action.status)}
            type="button"
          >
            <action.icon aria-hidden="true" className="size-3.5" />
            {action.label}
          </button>
        ) : null}
        {task.status === "TODO" || task.status === "IN_PROGRESS" ? (
          <button
            aria-label={`Hủy ${task.title}`}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-red-200 px-3 text-xs font-bold text-red-800 disabled:opacity-60"
            disabled={isSaving}
            onClick={() => onTransition(task, "CANCELLED")}
            type="button"
          >
            <XCircle aria-hidden="true" className="size-3.5" />
            Hủy
          </button>
        ) : null}
      </div>
    </article>
  );
}
