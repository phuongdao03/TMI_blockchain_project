"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Search, UsersRound, X } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  ApiError,
  hrAdminOvertimeApi,
  hrDepartmentApi,
} from "@/lib/api/client";
import type {
  AdminOvertimeRequest,
  OvertimeRequestStatus,
} from "@/lib/api/types";
import { HrReportDownload } from "@/components/hr/hr-report-download";

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
type Target = { request: AdminOvertimeRequest; action: "approve" | "reject" };

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

export function AdminOvertimeWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [status, setStatus] = useState<OvertimeRequestStatus | "">("");
  const [target, setTarget] = useState<Target | null>(null);
  const [note, setNote] = useState("");
  const departments = useQuery({
    queryKey: ["hr", "departments", "overtime-filter"],
    queryFn: () => hrDepartmentApi.list({ pageSize: 100 }),
  });
  const overtime = useQuery({
    queryKey: ["hr", "admin-overtime-requests", search, departmentId, status],
    queryFn: () =>
      hrAdminOvertimeApi.list({
        search: search || undefined,
        departmentId: departmentId || undefined,
        status: status || undefined,
        pageSize: 100,
      }),
  });
  const decide = useMutation({
    mutationFn: (current: Target) =>
      hrAdminOvertimeApi.decide(current.request.id, current.action, {
        decisionNote: note.trim() || null,
      }),
    onSuccess: () => {
      setTarget(null);
      setNote("");
      void queryClient.invalidateQueries({
        queryKey: ["hr", "admin-overtime-requests"],
      });
    },
  });
  const rows = overtime.data?.data ?? [];

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }
  function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!target) return;
    const label = target.action === "approve" ? "duyệt" : "từ chối";
    if (
      window.confirm(
        `Xác nhận ${label} yêu cầu tăng ca của ${target.request.employeeName}? Thay đổi sẽ được ghi vào audit log.`,
      )
    )
      decide.mutate(target);
  }

  return (
    <section
      aria-labelledby="admin-overtime-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="rounded-3xl border border-neutral-800 bg-neutral-950 px-6 py-7 text-white sm:px-8">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">
          <UsersRound className="size-4" /> Điều hành nhân sự
        </p>
        <h1
          className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
          id="admin-overtime-title"
        >
          Duyệt tăng ca
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
          Rà soát yêu cầu theo thời gian thực tế. Mọi quyết định có audit và
          thông báo trong ứng dụng; chưa tự suy diễn rate hoặc compensation.
        </p>
      </header>
      <form
        className="grid gap-3 rounded-2xl border border-neutral-200 bg-white p-4 md:grid-cols-3 xl:grid-cols-[1.3fr_13rem_11rem_auto]"
        onSubmit={submitFilters}
      >
        <label className="text-sm font-bold text-neutral-800">
          Tìm nhân viên
          <span className="relative mt-2 block">
            <Search className="absolute left-3 top-3.5 size-4 text-neutral-400" />
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
              setStatus(event.target.value as OvertimeRequestStatus | "")
            }
            value={status}
          >
            <option value="">Tất cả</option>
            {Object.entries(labels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white"
          type="submit"
        >
          Áp dụng
        </button>
      </form>
      <HrReportDownload
        download={() =>
          hrAdminOvertimeApi.exportXlsx({
            search: search || undefined,
            departmentId: departmentId || undefined,
            status: status || undefined,
          })
        }
        errorMessage="Không thể tải báo cáo tăng ca."
        filename="hr-overtime.xlsx"
      />
      {target ? (
        <form
          className={`grid gap-4 rounded-2xl border p-5 md:grid-cols-[1fr_20rem] ${target.action === "approve" ? "border-emerald-200 bg-emerald-50/60" : "border-red-200 bg-red-50/60"}`}
          onSubmit={confirm}
        >
          <div>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-neutral-500">
                  Xử lý có kiểm soát
                </p>
                <h2 className="mt-2 text-xl font-bold text-neutral-950">
                  {target.action === "approve" ? "Duyệt" : "Từ chối"} yêu cầu
                  của {target.request.employeeName}
                </h2>
                <p className="mt-1 text-sm text-neutral-600">
                  {displayTime(target.request.startAt)} –{" "}
                  {displayTime(target.request.endAt)}
                </p>
              </div>
              <button
                aria-label="Đóng biểu mẫu xử lý tăng ca"
                className="rounded-lg p-2 text-neutral-600 hover:bg-white"
                onClick={() => setTarget(null)}
                type="button"
              >
                <X className="size-5" />
              </button>
            </div>
            <label className="mt-5 block text-sm font-bold text-neutral-800">
              Ghi chú quyết định{" "}
              <span className="font-normal text-neutral-500">
                (không bắt buộc)
              </span>
              <textarea
                className={`${fieldClass} min-h-24 py-3`}
                maxLength={2000}
                onChange={(event) => setNote(event.target.value)}
                value={note}
              />
            </label>
          </div>
          <div className="flex flex-col justify-end gap-3">
            {decide.error ? (
              <p className="text-sm font-semibold text-red-700" role="alert">
                {apiMessage(decide.error)}
              </p>
            ) : null}
            <button
              className={`min-h-11 rounded-xl px-5 text-sm font-bold ${target.action === "approve" ? "bg-emerald-500 text-neutral-950" : "bg-red-700 text-white"}`}
              disabled={decide.isPending}
              type="submit"
            >
              {decide.isPending
                ? "Đang lưu..."
                : `Xác nhận ${target.action === "approve" ? "duyệt" : "từ chối"}`}
            </button>
            <button
              className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800"
              onClick={() => setTarget(null)}
              type="button"
            >
              Hủy
            </button>
          </div>
        </form>
      ) : null}
      <section
        aria-labelledby="overtime-list-title"
        className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white"
      >
        <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-5 py-3">
          <h2
            className="text-sm font-bold text-neutral-950"
            id="overtime-list-title"
          >
            Danh sách yêu cầu
          </h2>
          <span className="text-xs font-semibold text-neutral-500">
            {overtime.data?.meta.total ?? 0} yêu cầu
          </span>
        </div>
        <table className="min-w-[1050px] w-full text-left">
          <thead className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-5 py-3">Nhân viên</th>
              <th className="px-5 py-3">Thời gian</th>
              <th className="px-5 py-3">Lý do</th>
              <th className="px-5 py-3">Trạng thái</th>
              <th className="px-5 py-3">Phản hồi</th>
              <th className="px-5 py-3">
                <span className="sr-only">Xử lý</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {overtime.isPending ? (
              <tr>
                <td className="p-5" colSpan={6}>
                  <div
                    aria-label="Đang tải yêu cầu tăng ca"
                    className="h-14 animate-pulse rounded-xl bg-neutral-100"
                  />
                </td>
              </tr>
            ) : null}
            {overtime.isError ? (
              <tr>
                <td className="p-8 text-center" colSpan={6}>
                  <CircleAlert className="mx-auto size-8 text-red-700" />
                  <p className="mt-3 font-bold">
                    Không tải được danh sách tăng ca
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {apiMessage(overtime.error)}
                  </p>
                  <button
                    className="mt-3 text-sm font-bold text-primary-700"
                    onClick={() => void overtime.refetch()}
                    type="button"
                  >
                    Thử lại
                  </button>
                </td>
              </tr>
            ) : null}
            {!overtime.isPending && !overtime.isError && rows.length === 0 ? (
              <tr>
                <td
                  className="p-10 text-center text-sm text-neutral-600"
                  colSpan={6}
                >
                  Không có yêu cầu tăng ca phù hợp.
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
                <td className="px-5 py-4 text-sm text-neutral-700">
                  {displayTime(item.startAt)}
                  <br />
                  {displayTime(item.endAt)}
                </td>
                <td className="max-w-72 px-5 py-4 text-sm text-neutral-700">
                  {item.reason}
                </td>
                <td className="px-5 py-4">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-bold ${tones[item.status]}`}
                  >
                    {labels[item.status]}
                  </span>
                </td>
                <td className="max-w-56 px-5 py-4 text-sm text-neutral-700">
                  {item.decisionNote ?? "—"}
                </td>
                <td className="px-5 py-4">
                  {item.status === "PENDING" ? (
                    <div className="flex gap-2">
                      <button
                        className="min-h-9 rounded-lg bg-emerald-500 px-3 text-xs font-bold text-neutral-950"
                        onClick={() => {
                          setTarget({ request: item, action: "approve" });
                          setNote("");
                        }}
                        type="button"
                      >
                        Duyệt
                      </button>
                      <button
                        className="min-h-9 rounded-lg border border-red-200 px-3 text-xs font-bold text-red-800"
                        onClick={() => {
                          setTarget({ request: item, action: "reject" });
                          setNote("");
                        }}
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
