"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarRange,
  CircleAlert,
  ClipboardCheck,
  Search,
  UsersRound,
  X,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import { ApiError, hrAdminLeaveApi, hrDepartmentApi } from "@/lib/api/client";
import type { AdminLeaveRequest, LeaveRequestStatus } from "@/lib/api/types";
import { HrReportDownload } from "@/components/hr/hr-report-download";

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

type DecisionAction = "approve" | "reject";

type DecisionTarget = {
  request: AdminLeaveRequest;
  action: DecisionAction;
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

export function AdminLeaveWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [leaveStatus, setLeaveStatus] = useState<LeaveRequestStatus | "">("");
  const [startDateFrom, setStartDateFrom] = useState("");
  const [startDateTo, setStartDateTo] = useState("");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [decisionTarget, setDecisionTarget] = useState<DecisionTarget | null>(
    null,
  );
  const [decisionNote, setDecisionNote] = useState("");
  const departments = useQuery({
    queryKey: ["hr", "departments", "leave-filter"],
    queryFn: () => hrDepartmentApi.list({ pageSize: 100 }),
  });
  const leaveRequests = useQuery({
    queryKey: [
      "hr",
      "admin-leave-requests",
      search,
      departmentId,
      leaveStatus,
      startDateFrom,
      startDateTo,
    ],
    queryFn: () =>
      hrAdminLeaveApi.list({
        search: search || undefined,
        departmentId: departmentId || undefined,
        status: leaveStatus || undefined,
        startDateFrom: startDateFrom || undefined,
        startDateTo: startDateTo || undefined,
        pageSize: 100,
      }),
  });
  const decide = useMutation({
    mutationFn: (target: DecisionTarget) =>
      hrAdminLeaveApi.decide(target.request.id, target.action, {
        decisionNote: decisionNote.trim() || null,
      }),
    onSuccess: () => {
      setDecisionTarget(null);
      setDecisionNote("");
      void queryClient.invalidateQueries({
        queryKey: ["hr", "admin-leave-requests"],
      });
    },
  });
  const rows = leaveRequests.data?.data ?? [];

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (startDateFrom && startDateTo && startDateFrom > startDateTo) {
      setFilterError("Ngày bắt đầu không thể sau ngày kết thúc.");
      return;
    }
    setFilterError(null);
    setSearch(searchDraft.trim());
  }

  function beginDecision(request: AdminLeaveRequest, action: DecisionAction) {
    setDecisionTarget({ request, action });
    setDecisionNote("");
  }

  function confirmDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!decisionTarget) return;
    const actionLabel =
      decisionTarget.action === "approve" ? "duyệt" : "từ chối";
    if (
      window.confirm(
        `Xác nhận ${actionLabel} đơn nghỉ của ${decisionTarget.request.employeeName}? Thay đổi sẽ được ghi vào audit log.`,
      )
    ) {
      decide.mutate(decisionTarget);
    }
  }

  return (
    <section
      aria-labelledby="admin-leave-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <div className="absolute inset-y-0 right-0 w-2/5 bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.18),transparent_68%)]" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
              <UsersRound aria-hidden="true" className="size-4" /> Điều hành
              nhân sự
            </p>
            <h1
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
              id="admin-leave-title"
            >
              Duyệt nghỉ phép
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Xem toàn bộ đơn, xử lý từng yêu cầu rõ ràng và gửi thông báo kết
              quả trực tiếp đến nhân viên. Chưa có cơ chế tự trừ số dư.
            </p>
          </div>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-100">
            <ClipboardCheck
              aria-hidden="true"
              className="size-4 text-emerald-300"
            />
            Duyệt có audit
          </p>
        </div>
      </header>

      <form
        className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-2 xl:grid-cols-[1.3fr_13rem_11rem_10rem_10rem_auto]"
        onSubmit={submitFilters}
      >
        <label className="text-sm font-bold text-neutral-800">
          Tìm nhân viên
          <span className="relative mt-2 block">
            <Search
              aria-hidden="true"
              className="absolute left-3 top-3.5 size-4 text-neutral-400"
            />
            <input
              className={`${fieldClass} mt-0 pl-10`}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Mã, tên hoặc email"
              value={searchDraft}
            />
          </span>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Phòng ban
          <select
            className={fieldClass}
            onChange={(event) => setDepartmentId(event.target.value)}
            value={departmentId}
          >
            <option value="">Tất cả phòng ban</option>
            {departments.data?.data.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Trạng thái
          <select
            className={fieldClass}
            onChange={(event) =>
              setLeaveStatus(event.target.value as LeaveRequestStatus | "")
            }
            value={leaveStatus}
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
          Từ ngày
          <input
            className={fieldClass}
            onChange={(event) => setStartDateFrom(event.target.value)}
            type="date"
            value={startDateFrom}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Đến ngày
          <input
            className={fieldClass}
            onChange={(event) => setStartDateTo(event.target.value)}
            type="date"
            value={startDateTo}
          />
        </label>
        <button
          className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng
        </button>
        {filterError ? (
          <p
            className="text-sm font-semibold text-red-700 md:col-span-2 xl:col-span-6"
            role="alert"
          >
            {filterError}
          </p>
        ) : null}
      </form>

      <HrReportDownload
        download={() =>
          hrAdminLeaveApi.exportXlsx({
            search: search || undefined,
            departmentId: departmentId || undefined,
            status: leaveStatus || undefined,
            startDateFrom: startDateFrom || undefined,
            startDateTo: startDateTo || undefined,
          })
        }
        errorMessage="Không thể tải báo cáo nghỉ phép."
        filename="hr-leave.xlsx"
      />

      {decisionTarget ? (
        <DecisionForm
          error={decide.error ? apiMessage(decide.error) : null}
          isSaving={decide.isPending}
          note={decisionNote}
          onCancel={() => {
            setDecisionTarget(null);
            setDecisionNote("");
          }}
          onChange={setDecisionNote}
          onSubmit={confirmDecision}
          target={decisionTarget}
        />
      ) : null}

      <section
        aria-labelledby="leave-list-title"
        className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white"
      >
        <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-5 py-3">
          <h2
            className="text-sm font-bold text-neutral-950"
            id="leave-list-title"
          >
            Danh sách đơn nghỉ
          </h2>
          <span className="text-xs font-semibold text-neutral-500">
            {leaveRequests.data?.meta.total ?? 0} đơn
          </span>
        </div>
        <table className="min-w-[1090px] w-full text-left">
          <thead className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-5 py-3">Nhân viên</th>
              <th className="px-5 py-3">Loại & thời gian</th>
              <th className="px-5 py-3">Lý do</th>
              <th className="px-5 py-3">Trạng thái</th>
              <th className="px-5 py-3">Phản hồi</th>
              <th className="px-5 py-3">
                <span className="sr-only">Xử lý</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {leaveRequests.isPending ? (
              <tr>
                <td className="p-5" colSpan={6}>
                  <div
                    aria-label="Đang tải đơn nghỉ"
                    className="h-14 animate-pulse rounded-xl bg-neutral-100"
                  />
                </td>
              </tr>
            ) : null}
            {leaveRequests.isError ? (
              <tr>
                <td className="p-8 text-center" colSpan={6}>
                  <CircleAlert
                    aria-hidden="true"
                    className="mx-auto size-8 text-red-700"
                  />
                  <p className="mt-3 font-bold text-neutral-950">
                    Không tải được danh sách đơn nghỉ
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {apiMessage(leaveRequests.error)}
                  </p>
                  <button
                    className="mt-3 text-sm font-bold text-primary-700"
                    onClick={() => void leaveRequests.refetch()}
                    type="button"
                  >
                    Thử lại
                  </button>
                </td>
              </tr>
            ) : null}
            {!leaveRequests.isPending &&
            !leaveRequests.isError &&
            rows.length === 0 ? (
              <tr>
                <td className="p-10 text-center" colSpan={6}>
                  <CalendarRange
                    aria-hidden="true"
                    className="mx-auto size-9 text-neutral-400"
                  />
                  <p className="mt-3 font-bold text-neutral-950">
                    Không có đơn nghỉ phù hợp
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    Thử thay đổi bộ lọc hoặc khoảng ngày.
                  </p>
                </td>
              </tr>
            ) : null}
            {rows.map((item) => (
              <tr className="border-t border-neutral-100" key={item.id}>
                <td className="px-5 py-4">
                  <p className="font-bold text-neutral-950">
                    {item.employeeName}
                  </p>
                  <p className="mt-1 font-mono text-xs text-neutral-500">
                    {item.employeeCode} · {item.departmentName}
                  </p>
                </td>
                <td className="px-5 py-4">
                  <p className="font-semibold text-neutral-900">
                    {item.leaveType}
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {formatRange(item.startDate, item.endDate)}
                  </p>
                </td>
                <td className="max-w-72 px-5 py-4 text-sm leading-5 text-neutral-700">
                  {item.reason}
                </td>
                <td className="px-5 py-4">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${statusStyle[item.status]}`}
                  >
                    {statusLabels[item.status]}
                  </span>
                </td>
                <td className="max-w-56 px-5 py-4 text-sm leading-5 text-neutral-700">
                  {item.decisionNote ?? "—"}
                </td>
                <td className="px-5 py-4">
                  {item.status === "PENDING" ? (
                    <div className="flex gap-2">
                      <button
                        className="min-h-9 rounded-lg bg-emerald-500 px-3 text-xs font-bold text-neutral-950 transition hover:bg-emerald-400"
                        onClick={() => beginDecision(item, "approve")}
                        type="button"
                      >
                        Duyệt
                      </button>
                      <button
                        className="min-h-9 rounded-lg border border-red-200 px-3 text-xs font-bold text-red-800 transition hover:bg-red-50"
                        onClick={() => beginDecision(item, "reject")}
                        type="button"
                      >
                        Từ chối
                      </button>
                    </div>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}

function DecisionForm({
  error,
  isSaving,
  note,
  onCancel,
  onChange,
  onSubmit,
  target,
}: {
  error: string | null;
  isSaving: boolean;
  note: string;
  onCancel: () => void;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  target: DecisionTarget;
}) {
  const isApproval = target.action === "approve";
  const actionLabel = isApproval ? "duyệt" : "từ chối";
  return (
    <form
      className={`grid gap-4 rounded-2xl border p-5 md:grid-cols-[1fr_20rem] ${isApproval ? "border-emerald-200 bg-emerald-50/60" : "border-red-200 bg-red-50/60"}`}
      onSubmit={onSubmit}
    >
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p
              className={`text-xs font-bold uppercase tracking-[0.14em] ${isApproval ? "text-emerald-800" : "text-red-800"}`}
            >
              Xử lý có kiểm soát
            </p>
            <h2 className="mt-2 text-xl font-bold text-neutral-950">
              {isApproval ? "Duyệt" : "Từ chối"} đơn của{" "}
              {target.request.employeeName}
            </h2>
            <p className="mt-1 text-sm text-neutral-600">
              {target.request.leaveType} ·{" "}
              {formatRange(target.request.startDate, target.request.endDate)}
            </p>
          </div>
          <button
            aria-label="Đóng biểu mẫu xử lý đơn nghỉ"
            className="rounded-lg p-2 text-neutral-600 hover:bg-white/70"
            onClick={onCancel}
            type="button"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        <label className="mt-5 block text-sm font-bold text-neutral-800">
          Ghi chú quyết định{" "}
          <span className="font-normal text-neutral-500">(không bắt buộc)</span>
          <textarea
            className={`${fieldClass} min-h-24 py-3`}
            maxLength={2000}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Ví dụ: Đã thống nhất lịch bàn giao"
            value={note}
          />
        </label>
        <p className="mt-3 text-xs leading-5 text-neutral-600">
          Lý do nghỉ và ghi chú quyết định không được sao chép vào audit log;
          nhân viên sẽ nhận thông báo kết quả trong ứng dụng.
        </p>
      </div>
      <div className="flex flex-col justify-end gap-3">
        {error ? (
          <p className="text-sm font-semibold text-red-700" role="alert">
            {error}
          </p>
        ) : null}
        <button
          className={`min-h-11 rounded-xl px-5 text-sm font-bold disabled:opacity-60 ${isApproval ? "bg-emerald-500 text-neutral-950 hover:bg-emerald-400" : "bg-red-700 text-white hover:bg-red-800"}`}
          disabled={isSaving}
          type="submit"
        >
          {isSaving ? "Đang lưu..." : `Xác nhận ${actionLabel}`}
        </button>
        <button
          className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800"
          onClick={onCancel}
          type="button"
        >
          Hủy
        </button>
      </div>
    </form>
  );
}
