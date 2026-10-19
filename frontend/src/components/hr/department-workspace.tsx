"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRightLeft,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ClipboardList,
  Pencil,
  Plus,
  Search,
  Sparkles,
  UsersRound,
  X,
} from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import {
  ApiError,
  hrDepartmentApi,
  hrEmployeeApi,
  staffAccountsApi,
  taskAdminApi,
  workAllocationAdminApi,
} from "@/lib/api/client";
import { HrReportDownload } from "@/components/hr/hr-report-download";
import type {
  Department,
  WorkAllocationHandoff,
  WorkTask,
} from "@/lib/api/types";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";

const fieldClass =
  "min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

export function DepartmentWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<Department | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editManagerEmployeeId, setEditManagerEmployeeId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });
  const [handoffEmployeeId, setHandoffEmployeeId] = useState("");
  const [handoffTargetId, setHandoffTargetId] = useState("");

  const departments = useQuery({
    queryKey: ["hr", "departments", search],
    queryFn: () =>
      hrDepartmentApi.list({ search: search || undefined, pageSize: 100 }),
  });
  const editEmployees = useQuery({
    queryKey: ["hr", "department-employees", editing?.id],
    queryFn: () =>
      hrEmployeeApi.list({ departmentId: editing!.id, pageSize: 100 }),
    enabled: Boolean(editing),
  });
  const createDepartment = useMutation({
    mutationFn: () =>
      hrDepartmentApi.create({
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
      }),
    onSuccess: () => {
      setCreating(false);
      setCode("");
      setName("");
      setDescription("");
      void queryClient.invalidateQueries({ queryKey: ["hr", "departments"] });
    },
  });
  const rows = useMemo(() => departments.data?.data ?? [], [departments.data]);
  const effectiveSelectedId = rows.some((item) => item.id === selectedId)
    ? selectedId
    : (rows[0]?.id ?? "");
  const selectedDepartment =
    rows.find((item) => item.id === effectiveSelectedId) ?? null;
  const [
    year = new Date().getFullYear(),
    monthNumber = new Date().getMonth() + 1,
  ] = month.split("-").map(Number);
  const period = {
    startDate: `${month}-01`,
    endDate: `${month}-${String(new Date(year, monthNumber, 0).getDate()).padStart(2, "0")}`,
  };
  const overview = useQuery({
    queryKey: ["hr", "department-overview", effectiveSelectedId, month],
    queryFn: () => hrDepartmentApi.overview(effectiveSelectedId, period),
    enabled: Boolean(effectiveSelectedId),
  });
  const handoffMember = overview.data?.members.find(
    (member) => member.employeeId === handoffEmployeeId,
  );
  const handoffAccounts = useQuery({
    queryKey: ["staff-accounts", "department-handoff", effectiveSelectedId],
    queryFn: () =>
      staffAccountsApi.list({
        role: "MODERATOR",
        status: "ACTIVE",
        pageSize: 100,
      }),
    enabled: Boolean(handoffEmployeeId && handoffMember),
  });
  const eligibleHandoffUserIds = new Set(
    (handoffAccounts.data?.data ?? []).map((account) => account.id),
  );
  const handoffTasks = useQuery({
    queryKey: [
      "hr",
      "department-handoff-tasks",
      effectiveSelectedId,
      handoffEmployeeId,
    ],
    queryFn: async () => {
      async function loadTasks(status: "TODO" | "IN_PROGRESS") {
        const results: WorkTask[] = [];
        let page = 1;
        let total = 0;
        do {
          const response = await taskAdminApi.list({
            assigneeEmployeeId: handoffEmployeeId,
            status,
            page,
            pageSize: 100,
            sortBy: "dueAt",
            sortDirection: "asc",
          });
          results.push(...response.data);
          total = response.meta.total;
          page += 1;
        } while (results.length < total);
        return results;
      }
      const [todo, inProgress] = await Promise.all([
        loadTasks("TODO"),
        loadTasks("IN_PROGRESS"),
      ]);
      return [...todo, ...inProgress].sort(
        (left, right) =>
          (left.dueAt ? Date.parse(left.dueAt) : Infinity) -
          (right.dueAt ? Date.parse(right.dueAt) : Infinity),
      );
    },
    enabled: Boolean(handoffEmployeeId && handoffMember),
  });
  const openHandoffTasks = handoffTasks.data ?? [];
  const handoffAllocations = useQuery({
    queryKey: [
      "hr",
      "department-work-handoff-allocations",
      handoffMember?.userId,
    ],
    queryFn: async () => {
      const results: WorkAllocationHandoff[] = [];
      let page = 1;
      let total = 0;
      do {
        const response = await workAllocationAdminApi.handoffs(
          handoffMember!.userId!,
          page,
          100,
        );
        results.push(...response.data);
        total = response.meta.total;
        page += 1;
      } while (results.length < total);
      return results;
    },
    enabled: Boolean(handoffMember?.userId),
  });
  const openWorkAllocations = handoffAllocations.data ?? [];
  const availableHandoffTargets = (overview.data?.members ?? [])
    .filter(
      (member) =>
        member.employeeId !== handoffEmployeeId &&
        member.employmentStatus === "ACTIVE" &&
        Boolean(member.userId) &&
        eligibleHandoffUserIds.has(member.userId!),
    )
    .sort(
      (left, right) =>
        left.openTaskCount +
        left.openReviewCount -
        right.openTaskCount -
        right.openReviewCount,
    );
  const handoffMutation = useMutation({
    mutationFn: async (input: {
      taskIds: string[];
      allocationIds: string[];
      employeeId: string;
      fromUserId: string;
      toUserId: string;
    }) => {
      for (const taskId of input.taskIds) {
        await taskAdminApi.update(taskId, {
          assigneeEmployeeId: input.employeeId,
        });
      }
      for (const allocationId of input.allocationIds) {
        await workAllocationAdminApi.handoff(allocationId, {
          fromUserId: input.fromUserId,
          toUserId: input.toUserId,
        });
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["hr", "department-overview", effectiveSelectedId],
      });
      await queryClient.invalidateQueries({
        queryKey: [
          "hr",
          "department-handoff-tasks",
          effectiveSelectedId,
          handoffEmployeeId,
        ],
      });
      await queryClient.invalidateQueries({
        queryKey: [
          "hr",
          "department-work-handoff-allocations",
          handoffMember?.userId,
        ],
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["work-allocations"] }),
        queryClient.invalidateQueries({ queryKey: ["my-work-allocations"] }),
      ]);
    },
    onError: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["hr", "department-overview", effectiveSelectedId],
      });
      await queryClient.invalidateQueries({
        queryKey: [
          "hr",
          "department-handoff-tasks",
          effectiveSelectedId,
          handoffEmployeeId,
        ],
      });
      await queryClient.invalidateQueries({
        queryKey: [
          "hr",
          "department-work-handoff-allocations",
          handoffMember?.userId,
        ],
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["work-allocations"] }),
        queryClient.invalidateQueries({ queryKey: ["my-work-allocations"] }),
      ]);
    },
  });
  const updateDepartment = useMutation({
    mutationFn: () =>
      hrDepartmentApi.update(editing!.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
        managerEmployeeId: editManagerEmployeeId || null,
      }),
    onSuccess: () => {
      setEditing(null);
      void queryClient.invalidateQueries({ queryKey: ["hr", "departments"] });
    },
  });

  function startEdit(department: Department) {
    setEditing(department);
    setEditName(department.name);
    setEditDescription(department.description ?? "");
    setEditManagerEmployeeId(department.managerEmployeeId ?? "");
    updateDepartment.reset();
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  function submitCreate(event: FormEvent) {
    event.preventDefault();
    createDepartment.mutate();
  }

  return (
    <section
      className="workspace-screen mx-auto max-w-7xl space-y-6 pb-12"
      aria-labelledby="departments-title"
    >
      <WorkspacePageHeader
        action={
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[var(--theme-accent)] px-5 text-sm font-bold text-[var(--theme-accent-contrast)] transition hover:opacity-90 active:scale-[0.98]"
            onClick={() => setCreating(true)}
            type="button"
          >
            <Plus className="size-4" aria-hidden="true" /> Thêm phòng ban
          </button>
        }
        description="Theo dõi nhân sự, việc đang xử lý và yêu cầu cần duyệt của từng phòng ban."
        icon={Sparkles}
        id="departments-title"
        section="Không gian nhân sự"
        title="Cơ cấu phòng ban"
      />

      <form className="flex gap-2" onSubmit={submitSearch}>
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Tìm phòng ban</span>
          <Search
            className="absolute left-4 top-3.5 size-4 text-neutral-400"
            aria-hidden="true"
          />
          <input
            className={`${fieldClass} pl-11`}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Tên hoặc mã phòng ban"
          />
        </label>
        <button
          className="min-h-11 shrink-0 rounded-xl border border-neutral-300 bg-white px-4 text-sm font-bold text-neutral-900 transition hover:bg-neutral-50"
          type="submit"
        >
          Tìm kiếm
        </button>
      </form>

      <HrReportDownload
        download={() =>
          hrDepartmentApi.exportXlsx({ search: search || undefined })
        }
        errorMessage="Không thể tải báo cáo phòng ban."
        filename="hr-departments.xlsx"
      />

      {creating ? (
        <form
          className="hr-department-form grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 md:grid-cols-2"
          onSubmit={submitCreate}
        >
          <div className="flex items-center justify-between md:col-span-2">
            <div>
              <h2 className="text-lg font-bold text-neutral-950">
                Phòng ban mới
              </h2>
              <p className="mt-1 text-sm text-neutral-600">
                Mã phòng ban là duy nhất và sẽ được chuẩn hóa thành chữ in hoa.
              </p>
            </div>
            <button
              aria-label="Đóng biểu mẫu"
              className="rounded-lg p-2 text-neutral-600 hover:bg-white"
              onClick={() => setCreating(false)}
              type="button"
            >
              <X className="size-5" />
            </button>
          </div>
          <label className="text-sm font-bold text-neutral-800">
            Mã phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={32}
              onChange={(e) => setCode(e.target.value)}
              required
              value={code}
            />
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Tên phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={160}
              onChange={(e) => setName(e.target.value)}
              required
              value={name}
            />
          </label>
          <label className="text-sm font-bold text-neutral-800 md:col-span-2">
            Mô tả
            <textarea
              className={`${fieldClass} mt-2 min-h-24 py-3`}
              maxLength={2000}
              onChange={(e) => setDescription(e.target.value)}
              value={description}
            />
          </label>
          {createDepartment.error ? (
            <p className="text-sm font-semibold text-red-700 md:col-span-2">
              {createDepartment.error instanceof ApiError
                ? createDepartment.error.message
                : "Không thể tạo phòng ban."}
            </p>
          ) : null}
          <div className="flex justify-end md:col-span-2">
            <button
              className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white disabled:opacity-50"
              disabled={createDepartment.isPending}
              type="submit"
            >
              {createDepartment.isPending ? "Đang lưu..." : "Lưu phòng ban"}
            </button>
          </div>
        </form>
      ) : null}

      {editing ? (
        <form
          className="hr-department-form grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-900 dark:bg-emerald-950/30 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            updateDepartment.mutate();
          }}
        >
          <div className="flex items-center justify-between sm:col-span-2">
            <h2 className="text-base font-bold text-neutral-950 dark:text-white">
              Chỉnh sửa phòng ban · {editing.code}
            </h2>
            <button
              aria-label="Đóng chỉnh sửa"
              className="rounded-lg p-2 dark:text-white"
              onClick={() => setEditing(null)}
              type="button"
            >
              <X className="size-5" />
            </button>
          </div>
          <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Tên phòng ban
            <input
              className={`${fieldClass} mt-2`}
              maxLength={160}
              minLength={2}
              onChange={(event) => setEditName(event.target.value)}
              required
              value={editName}
            />
          </label>
          <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Mô tả
            <input
              className={`${fieldClass} mt-2`}
              maxLength={2000}
              onChange={(event) => setEditDescription(event.target.value)}
              value={editDescription}
            />
          </label>
          <label className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 sm:col-span-2">
            Người phụ trách
            <select
              className={`${fieldClass} mt-2`}
              onChange={(event) => setEditManagerEmployeeId(event.target.value)}
              value={editManagerEmployeeId}
              disabled={editEmployees.isError}
            >
              <option value="">Chưa phân công</option>
              {(editEmployees.data?.data ?? []).map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.fullName} · {employee.position}
                </option>
              ))}
            </select>
          </label>
          {editEmployees.isError ? (
            <p className="text-sm text-amber-800 sm:col-span-2" role="status">
              Không tải được danh sách nhân viên. Hãy tải lại trước khi đổi
              người phụ trách.
            </p>
          ) : null}
          {updateDepartment.isError ? (
            <p
              className="text-sm font-semibold text-red-700 dark:text-red-300 sm:col-span-2"
              role="alert"
            >
              {updateDepartment.error instanceof ApiError
                ? updateDepartment.error.message
                : "Không thể cập nhật phòng ban."}
            </p>
          ) : null}
          <div className="flex justify-end sm:col-span-2">
            <button
              className="min-h-11 rounded-xl bg-emerald-700 px-5 text-sm font-bold text-white disabled:opacity-50"
              disabled={updateDepartment.isPending}
              type="submit"
            >
              {updateDepartment.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </button>
          </div>
        </form>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[minmax(15rem,0.75fr)_minmax(0,1.5fr)]">
        <section
          aria-label="Danh sách phòng ban"
          className="min-w-0 rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5"
        >
          <div className="mb-3 flex items-center gap-2 text-sm font-bold text-neutral-900">
            <Building2 className="size-4 text-primary-700" /> Phòng ban
          </div>
          {departments.isPending ? (
            <div className="space-y-3" aria-label="Đang tải">
              <div className="h-16 animate-pulse rounded-xl bg-neutral-100" />
              <div className="h-16 animate-pulse rounded-xl bg-neutral-100" />
            </div>
          ) : null}
          {departments.isError ? (
            <div className="py-6 text-center">
              <p className="font-bold text-neutral-900">
                Không tải được phòng ban
              </p>
              <button
                className="mt-3 text-sm font-bold text-primary-700"
                onClick={() => void departments.refetch()}
                type="button"
              >
                Thử lại
              </button>
            </div>
          ) : null}
          {!departments.isPending &&
          !departments.isError &&
          rows.length === 0 ? (
            <div className="py-8 text-center">
              <Building2 className="mx-auto size-8 text-neutral-400" />
              <p className="mt-3 font-bold text-neutral-950">
                Chưa có phòng ban
              </p>
            </div>
          ) : null}
          <div className="divide-y divide-neutral-100">
            {rows.map((department) => (
              <article
                className="flex min-w-0 items-start gap-2 py-3 first:pt-1 last:pb-1"
                key={department.id}
              >
                <button
                  aria-current={
                    effectiveSelectedId === department.id ? "true" : undefined
                  }
                  className={`min-h-12 min-w-0 flex-1 rounded-xl px-3 py-2 text-left transition ${effectiveSelectedId === department.id ? "bg-primary-50 text-neutral-950" : "hover:bg-neutral-50"}`}
                  onClick={() => {
                    setSelectedId(department.id);
                    setHandoffEmployeeId("");
                    setHandoffTargetId("");
                    handoffMutation.reset();
                  }}
                  type="button"
                >
                  <span className="block truncate font-semibold">
                    {department.name}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-neutral-600">
                    {department.code} ·{" "}
                    {department.managerEmployeeId
                      ? "Đã có người phụ trách"
                      : "Chưa phân công phụ trách"}
                  </span>
                </button>
                <button
                  aria-label={`Sửa phòng ban ${department.name}`}
                  className="mt-1 inline-flex size-10 shrink-0 items-center justify-center rounded-lg text-neutral-600 hover:bg-neutral-100"
                  onClick={() => startEdit(department)}
                  type="button"
                >
                  <Pencil aria-hidden="true" className="size-4" />
                </button>
              </article>
            ))}
          </div>
        </section>

        <section
          aria-label="Tổng quan phòng ban"
          className="min-w-0 space-y-4 rounded-2xl border border-neutral-200 bg-white p-4 sm:p-6"
        >
          {selectedDepartment ? (
            <>
              <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    {selectedDepartment.code}
                  </p>
                  <h2 className="mt-1 break-words text-xl font-bold text-neutral-950 sm:text-2xl">
                    {selectedDepartment.name}
                  </h2>
                  <p className="mt-1 text-sm leading-5 text-neutral-600">
                    {selectedDepartment.description || "Chưa có mô tả."}
                  </p>
                  <p className="mt-2 text-sm font-medium text-neutral-700">
                    Người phụ trách:{" "}
                    {overview.data?.members.find(
                      (member) =>
                        member.employeeId ===
                        selectedDepartment.managerEmployeeId,
                    )?.fullName ?? "Chưa phân công"}
                  </p>
                </div>
                <label className="flex min-h-10 shrink-0 items-center gap-2 self-start rounded-lg border border-neutral-200 px-3 text-sm font-medium text-neutral-700">
                  <CalendarDays className="size-4 text-neutral-500" />
                  <span className="sr-only">Kỳ báo cáo</span>
                  <input
                    aria-label="Kỳ báo cáo"
                    className="min-w-0 bg-transparent py-2 outline-none"
                    onChange={(event) => {
                      if (event.target.value) setMonth(event.target.value);
                    }}
                    type="month"
                    value={month}
                  />
                </label>
              </header>

              {overview.isPending ? (
                <p
                  className="rounded-xl bg-neutral-50 p-4 text-sm text-neutral-600"
                  role="status"
                >
                  Đang tải tình hình phòng ban…
                </p>
              ) : null}
              {overview.isError ? (
                <p
                  className="rounded-xl bg-red-50 p-4 text-sm text-red-800"
                  role="alert"
                >
                  Không tải được tình hình phòng ban. Hãy thử tải lại trang.
                </p>
              ) : null}
              {overview.data ? (
                <>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      {
                        Icon: UsersRound,
                        label: "Đang làm",
                        value: overview.data.activeMemberCount,
                      },
                      {
                        Icon: ClipboardList,
                        label: "Đang xử lý",
                        value: overview.data.openTaskCount,
                      },
                      {
                        Icon: Clock3,
                        label: "Quá hạn",
                        value:
                          overview.data.overdueTaskCount +
                          overview.data.overdueReviewCount,
                      },
                      {
                        Icon: CheckCircle2,
                        label: "Hoàn tất kỳ này",
                        value: overview.data.completedTaskCount,
                      },
                    ].map(({ Icon, label, value }) => (
                      <div
                        className="min-w-0 rounded-xl bg-neutral-50 px-3 py-3"
                        key={label}
                      >
                        <Icon
                          className="size-4 text-primary-700"
                          aria-hidden="true"
                        />
                        <p className="mt-2 text-xl font-bold text-neutral-950">
                          {value}
                        </p>
                        <p className="text-xs leading-4 text-neutral-600">
                          {label}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-600">
                    <span>{overview.data.memberCount} nhân sự</span>
                    <span>{overview.data.onLeaveMemberCount} đang nghỉ</span>
                    <span>
                      Thời gian xử lý trung bình:{" "}
                      {overview.data.averageTaskCompletionHours === null
                        ? "Chưa có dữ liệu"
                        : `${overview.data.averageTaskCompletionHours.toFixed(1)} giờ`}
                    </span>
                  </div>

                  <section aria-labelledby="department-requests-title">
                    <h3
                      className="text-sm font-bold text-neutral-900"
                      id="department-requests-title"
                    >
                      Yêu cầu cần xem
                    </h3>
                    <div className="mt-2 grid gap-2 sm:grid-cols-3">
                      {[
                        {
                          href: "/admin/leave",
                          label: "Nghỉ phép",
                          count: overview.data.pendingLeaveCount,
                        },
                        {
                          href: "/admin/overtime",
                          label: "Tăng ca",
                          count: overview.data.pendingOvertimeCount,
                        },
                        {
                          href: "/admin/attendance",
                          label: "Chấm công",
                          count: overview.data.pendingAttendanceCount,
                        },
                      ].map(({ href, label, count }) => (
                        <Link
                          className="flex min-h-11 items-center justify-between gap-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
                          href={href}
                          key={href}
                        >
                          <span className="truncate">{label}</span>
                          <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-bold">
                            {count}
                          </span>
                        </Link>
                      ))}
                    </div>
                  </section>

                  <section aria-labelledby="department-members-title">
                    <div className="flex items-center justify-between gap-3">
                      <h3
                        className="text-sm font-bold text-neutral-900"
                        id="department-members-title"
                      >
                        Thành viên & khối lượng việc
                      </h3>
                      <span className="shrink-0 text-xs text-neutral-500">
                        Ít việc trước
                      </span>
                    </div>
                    <div className="mt-2 divide-y divide-neutral-100">
                      {[...overview.data.members]
                        .sort(
                          (left, right) =>
                            left.openReviewCount +
                            left.openTaskCount -
                            right.openReviewCount -
                            right.openTaskCount,
                        )
                        .map((member) => (
                          <div
                            className="flex min-w-0 items-center justify-between gap-3 py-3"
                            key={member.employeeId}
                          >
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-neutral-900">
                                {member.fullName}
                                {member.employeeId ===
                                selectedDepartment.managerEmployeeId
                                  ? " · Phụ trách"
                                  : ""}
                              </p>
                              <p className="truncate text-xs text-neutral-600">
                                {member.position} · {member.openTaskCount} việc
                                · {member.openReviewCount} hồ sơ
                              </p>
                            </div>
                            <div className="shrink-0 text-right text-xs">
                              <p className="font-semibold text-neutral-800">
                                {member.overdueTaskCount +
                                  member.overdueReviewCount}{" "}
                                quá hạn
                              </p>
                              <p className="text-neutral-500">
                                {member.employmentStatus === "ACTIVE"
                                  ? "Đang làm việc"
                                  : member.employmentStatus === "ON_LEAVE"
                                    ? "Đang nghỉ"
                                    : "Không hoạt động"}
                              </p>
                            </div>
                          </div>
                        ))}
                      {overview.data.members.length === 0 ? (
                        <p className="py-4 text-sm text-neutral-600">
                          Phòng ban chưa có thành viên.
                        </p>
                      ) : null}
                    </div>
                  </section>

                  <section
                    className="rounded-xl border border-neutral-200 p-3 sm:p-4"
                    aria-labelledby="department-handoff-title"
                  >
                    <div className="flex items-start gap-3">
                      <ArrowRightLeft
                        className="mt-0.5 size-4 shrink-0 text-primary-700"
                        aria-hidden="true"
                      />
                      <div className="min-w-0 flex-1">
                        <h3
                          className="text-sm font-bold text-neutral-900"
                          id="department-handoff-title"
                        >
                          Bàn giao việc chưa xong
                        </h3>
                        <p className="mt-1 text-xs leading-5 text-neutral-600">
                          Chọn thành viên sắp chuyển nhóm hoặc nghỉ việc để xem
                          việc đang mở và giao lại.
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <select
                        aria-label="Thành viên cần bàn giao"
                        className={fieldClass}
                        onChange={(event) => {
                          setHandoffEmployeeId(event.target.value);
                          setHandoffTargetId("");
                          handoffMutation.reset();
                        }}
                        value={handoffEmployeeId}
                      >
                        <option value="">Chọn thành viên</option>
                        {overview.data.members.map((member) => (
                          <option
                            key={member.employeeId}
                            value={member.employeeId}
                          >
                            {member.fullName}
                          </option>
                        ))}
                      </select>
                      <select
                        aria-label="Người nhận bàn giao"
                        className={fieldClass}
                        disabled={!handoffEmployeeId}
                        onChange={(event) =>
                          setHandoffTargetId(event.target.value)
                        }
                        value={handoffTargetId}
                      >
                        <option value="">Chọn người nhận</option>
                        {availableHandoffTargets.map((member) => (
                          <option
                            key={member.employeeId}
                            value={member.employeeId}
                          >
                            {member.fullName} ·{" "}
                            {member.openTaskCount + member.openReviewCount} việc
                            đang mở
                          </option>
                        ))}
                      </select>
                    </div>
                    {handoffEmployeeId && handoffAccounts.isPending ? (
                      <p className="mt-2 text-xs text-neutral-600">
                        Đang tìm người có thể nhận việc…
                      </p>
                    ) : null}
                    {handoffAccounts.isError ? (
                      <p className="mt-2 text-xs text-red-700" role="alert">
                        Không tải được danh sách người nhận.
                      </p>
                    ) : null}
                    {handoffEmployeeId &&
                    !handoffAccounts.isPending &&
                    availableHandoffTargets.length === 0 ? (
                      <p className="mt-2 text-xs text-amber-700">
                        Chưa có thành viên đủ điều kiện để nhận bàn giao.
                      </p>
                    ) : null}
                    {handoffEmployeeId ? (
                      <div className="mt-3">
                        {handoffTasks.isPending ||
                        (Boolean(handoffMember?.userId) &&
                          handoffAllocations.isPending) ? (
                          <p className="text-sm text-neutral-600">
                            Đang tải việc cần bàn giao…
                          </p>
                        ) : null}
                        {handoffTasks.isError ||
                        (Boolean(handoffMember?.userId) &&
                          handoffAllocations.isError) ? (
                          <p className="text-sm text-red-700" role="alert">
                            Không tải được danh sách việc. Kiểm tra quyền quản
                            lý công việc rồi thử lại.
                          </p>
                        ) : null}
                        {!handoffMember?.userId ? (
                          <p className="text-sm text-neutral-600">
                            Chưa có tài khoản để tra cứu công việc nhóm.
                          </p>
                        ) : null}
                        {handoffTasks.data &&
                        (!handoffMember?.userId || handoffAllocations.data) &&
                        openHandoffTasks.length + openWorkAllocations.length ===
                          0 ? (
                          <p className="text-sm text-neutral-600">
                            Thành viên này không có việc đang mở cần bàn giao.
                          </p>
                        ) : null}
                        {openHandoffTasks.length + openWorkAllocations.length >
                        0 ? (
                          <>
                            <p className="mb-1 text-xs font-semibold text-neutral-700">
                              Đầu việc
                            </p>
                            <ul className="max-h-36 divide-y divide-neutral-100 overflow-y-auto rounded-lg bg-neutral-50 px-3">
                              {openHandoffTasks.map((task) => (
                                <li className="py-2 text-sm" key={task.id}>
                                  <span className="block truncate font-medium text-neutral-900">
                                    {task.title}
                                  </span>
                                  <span className="text-xs text-neutral-600">
                                    {task.status === "IN_PROGRESS"
                                      ? "Đang thực hiện"
                                      : "Chưa bắt đầu"}
                                    {task.dueAt
                                      ? ` · Hạn ${new Date(task.dueAt).toLocaleDateString("vi-VN")}`
                                      : ""}
                                  </span>
                                </li>
                              ))}
                            </ul>
                            {openWorkAllocations.length > 0 ? (
                              <>
                                <p className="mb-1 mt-3 text-xs font-semibold text-neutral-700">
                                  Công việc nhóm
                                </p>
                                <ul className="max-h-36 divide-y divide-neutral-100 overflow-y-auto rounded-lg bg-neutral-50 px-3">
                                  {openWorkAllocations.map((work) => (
                                    <li
                                      className="py-2 text-sm"
                                      key={work.allocationId}
                                    >
                                      <span className="block truncate font-medium text-neutral-900">
                                        {work.objective}
                                      </span>
                                      <span className="text-xs text-neutral-600">
                                        {work.responsibility === "LEAD"
                                          ? "Phụ trách chính"
                                          : "Cùng thực hiện"}
                                        {work.dueAt
                                          ? ` · Hạn ${new Date(work.dueAt).toLocaleDateString("vi-VN")}`
                                          : ""}
                                      </span>
                                    </li>
                                  ))}
                                </ul>
                              </>
                            ) : null}
                            <button
                              className="mt-3 min-h-11 w-full rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                              disabled={
                                !handoffTargetId ||
                                handoffMutation.isPending ||
                                handoffTasks.isPending ||
                                (Boolean(handoffMember?.userId) &&
                                  handoffAllocations.isPending)
                              }
                              onClick={() =>
                                handoffMutation.mutate({
                                  taskIds: openHandoffTasks.map(
                                    (task) => task.id,
                                  ),
                                  allocationIds: openWorkAllocations.map(
                                    (work) => work.allocationId,
                                  ),
                                  employeeId: handoffTargetId,
                                  fromUserId: handoffMember?.userId ?? "",
                                  toUserId:
                                    availableHandoffTargets.find(
                                      (member) =>
                                        member.employeeId === handoffTargetId,
                                    )?.userId ?? "",
                                })
                              }
                              type="button"
                            >
                              {handoffMutation.isPending
                                ? "Đang bàn giao…"
                                : `Bàn giao ${openHandoffTasks.length + openWorkAllocations.length} mục`}
                            </button>
                          </>
                        ) : null}
                        {handoffMutation.isError ? (
                          <p className="mt-2 text-sm text-red-700" role="alert">
                            Một số việc chưa được chuyển. Danh sách đã được làm
                            mới; hãy thử lại hoặc chọn người nhận khác.
                          </p>
                        ) : null}
                        {handoffMutation.isSuccess ? (
                          <p
                            className="mt-2 text-sm font-medium text-emerald-800"
                            role="status"
                          >
                            Đã bàn giao việc. Người nhận được thông báo.
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </section>
                </>
              ) : null}
            </>
          ) : (
            <p className="py-8 text-center text-sm text-neutral-600">
              Chọn một phòng ban để xem tình hình.
            </p>
          )}
        </section>
      </div>
    </section>
  );
}
