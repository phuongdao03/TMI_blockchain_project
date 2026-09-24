"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarRange,
  ClipboardPenLine,
  Clock3,
  Search,
  UsersRound,
  X,
} from "lucide-react";
import { Fragment, type FormEvent, useState } from "react";

import {
  ApiError,
  hrAdminAttendanceApi,
  hrDepartmentApi,
} from "@/lib/api/client";
import type { AdminAttendance, AttendanceStatus } from "@/lib/api/types";
import { AttendanceLocationExceptionPanel } from "@/components/hr/attendance-location-exception-panel";
import { AdminAttendanceLocationEvidence } from "@/components/hr/admin-attendance-location-evidence";
import { HrReportDownload } from "@/components/hr/hr-report-download";

const fieldClass =
  "min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

const statusLabels: Record<AttendanceStatus, string> = {
  PRESENT: "Đúng giờ",
  LATE: "Đi muộn",
  ABSENT: "Vắng mặt",
  LEAVE: "Nghỉ phép",
  HALF_DAY: "Nửa ngày",
  OT: "Tăng ca",
  PENDING: "Chờ duyệt vị trí",
  REJECTED: "Từ chối vị trí",
};

const statusStyles: Record<AttendanceStatus, string> = {
  PRESENT: "bg-emerald-50 text-emerald-800",
  LATE: "bg-amber-50 text-amber-900",
  ABSENT: "bg-red-50 text-red-800",
  LEAVE: "bg-violet-50 text-violet-800",
  HALF_DAY: "bg-amber-50 text-amber-900",
  OT: "bg-sky-50 text-sky-800",
  PENDING: "bg-amber-50 text-amber-900 ring-1 ring-amber-200",
  REJECTED: "bg-red-50 text-red-800 ring-1 ring-red-200",
};

function isLocationDecisionStatus(status: AttendanceStatus) {
  return status === "PENDING" || status === "REJECTED";
}

type EditForm = {
  checkInAt: string;
  checkOutAt: string;
  status: AttendanceStatus;
  lateMinutes: string;
  earlyLeaveMinutes: string;
  note: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatTime(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function toLocalInput(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toEditForm(item: AdminAttendance): EditForm {
  return {
    checkInAt: toLocalInput(item.checkInAt),
    checkOutAt: toLocalInput(item.checkOutAt),
    status: item.status,
    lateMinutes: String(item.lateMinutes),
    earlyLeaveMinutes: String(item.earlyLeaveMinutes),
    note: item.note ?? "",
  };
}

function apiMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Không thể cập nhật bản ghi. Vui lòng thử lại.";
}

export function AdminAttendanceWorkspace() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [attendanceStatus, setAttendanceStatus] = useState<
    AttendanceStatus | ""
  >("");
  const [workDateFrom, setWorkDateFrom] = useState("");
  const [workDateTo, setWorkDateTo] = useState("");
  const [editing, setEditing] = useState<AdminAttendance | null>(null);
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(
    null,
  );
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const departments = useQuery({
    queryKey: ["hr", "departments", "attendance-filter"],
    queryFn: () => hrDepartmentApi.list({ pageSize: 100 }),
  });
  const attendance = useQuery({
    queryKey: [
      "hr",
      "admin-attendance",
      search,
      departmentId,
      attendanceStatus,
      workDateFrom,
      workDateTo,
    ],
    queryFn: () =>
      hrAdminAttendanceApi.list({
        search: search || undefined,
        departmentId: departmentId || undefined,
        status: attendanceStatus || undefined,
        workDateFrom: workDateFrom || undefined,
        workDateTo: workDateTo || undefined,
        pageSize: 100,
      }),
  });
  const updateAttendance = useMutation({
    mutationFn: () => {
      if (!editing || !editForm)
        throw new Error("Missing attendance edit target");
      return hrAdminAttendanceApi.update(editing.id, {
        checkInAt: editForm.checkInAt
          ? new Date(editForm.checkInAt).toISOString()
          : null,
        checkOutAt: editForm.checkOutAt
          ? new Date(editForm.checkOutAt).toISOString()
          : null,
        status: editForm.status,
        lateMinutes: Number(editForm.lateMinutes),
        earlyLeaveMinutes: Number(editForm.earlyLeaveMinutes),
        note: editForm.note.trim() || null,
      });
    },
    onSuccess: () => {
      setEditing(null);
      setEditForm(null);
      void queryClient.invalidateQueries({
        queryKey: ["hr", "admin-attendance"],
      });
    },
  });
  const rows = attendance.data?.data ?? [];

  function submitFilters(event: FormEvent) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  function beginEdit(item: AdminAttendance) {
    setEditing(item);
    setEditForm(toEditForm(item));
    setFormError(null);
  }

  function updateEditField(field: keyof EditForm, value: string) {
    setEditForm((current) =>
      current ? { ...current, [field]: value } : current,
    );
  }

  function submitEdit(event: FormEvent) {
    event.preventDefault();
    if (!editForm) return;
    if (
      editForm.checkInAt &&
      editForm.checkOutAt &&
      new Date(editForm.checkOutAt) <= new Date(editForm.checkInAt)
    ) {
      setFormError("Giờ ra phải sau giờ vào.");
      return;
    }
    if (!editForm.checkInAt && editForm.checkOutAt) {
      setFormError("Cần có giờ vào trước khi ghi giờ ra.");
      return;
    }
    setFormError(null);
    if (
      window.confirm(
        "Xác nhận điều chỉnh bản ghi chấm công? Thay đổi sẽ được lưu vào audit log.",
      )
    ) {
      updateAttendance.mutate();
    }
  }

  return (
    <section
      className="mx-auto max-w-7xl space-y-6 pb-12"
      aria-labelledby="admin-attendance-title"
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
              id="admin-attendance-title"
            >
              Chấm công toàn đội
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Theo dõi dữ liệu thực tế, lọc nhanh theo phòng ban và điều chỉnh
              có kiểm soát. Không có quy tắc chấm công tự động nào được suy diễn
              ở đây.
            </p>
          </div>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-100">
            <ClipboardPenLine
              aria-hidden="true"
              className="size-4 text-emerald-300"
            />{" "}
            Mọi điều chỉnh đều có audit
          </p>
        </div>
      </header>

      <AttendanceLocationExceptionPanel />

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
              className={`${fieldClass} pl-10`}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Mã, tên hoặc email"
              value={searchDraft}
            />
          </span>
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Phòng ban
          <select
            className={`${fieldClass} mt-2`}
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
            className={`${fieldClass} mt-2`}
            onChange={(event) =>
              setAttendanceStatus(event.target.value as AttendanceStatus | "")
            }
            value={attendanceStatus}
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
            className={`${fieldClass} mt-2`}
            onChange={(event) => setWorkDateFrom(event.target.value)}
            type="date"
            value={workDateFrom}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Đến ngày
          <input
            className={`${fieldClass} mt-2`}
            onChange={(event) => setWorkDateTo(event.target.value)}
            type="date"
            value={workDateTo}
          />
        </label>
        <button
          className="min-h-11 self-end rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white transition hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng
        </button>
      </form>

      <HrReportDownload
        download={() =>
          hrAdminAttendanceApi.exportXlsx({
            search: search || undefined,
            departmentId: departmentId || undefined,
            status: attendanceStatus || undefined,
            workDateFrom: workDateFrom || undefined,
            workDateTo: workDateTo || undefined,
          })
        }
        errorMessage="Không thể tải báo cáo chấm công."
        filename="hr-attendance.xlsx"
      />

      {editing && editForm ? (
        <EditAttendanceForm
          attendance={editing}
          error={
            formError ??
            (updateAttendance.error ? apiMessage(updateAttendance.error) : null)
          }
          form={editForm}
          isSaving={updateAttendance.isPending}
          onCancel={() => {
            setEditing(null);
            setEditForm(null);
          }}
          onChange={updateEditField}
          onSubmit={submitEdit}
        />
      ) : null}

      <section
        className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white"
        aria-labelledby="attendance-list-title"
      >
        <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-5 py-3">
          <h2
            className="text-sm font-bold text-neutral-950"
            id="attendance-list-title"
          >
            Danh sách bản ghi
          </h2>
          <span className="text-xs font-semibold text-neutral-500">
            {attendance.data?.meta.total ?? 0} bản ghi
          </span>
        </div>
        <table className="min-w-[1000px] w-full text-left">
          <thead className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-5 py-3">Nhân viên</th>
              <th className="px-5 py-3">Phòng ban</th>
              <th className="px-5 py-3">Ngày công</th>
              <th className="px-5 py-3">Giờ vào / ra</th>
              <th className="px-5 py-3">Trạng thái</th>
              <th className="px-5 py-3">Chênh lệch</th>
              <th aria-label="Thao tác" className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {attendance.isPending ? (
              <tr>
                <td className="p-5" colSpan={7}>
                  <div
                    aria-label="Đang tải chấm công"
                    className="h-14 animate-pulse rounded-xl bg-neutral-100"
                  />
                </td>
              </tr>
            ) : null}
            {attendance.isError ? (
              <tr>
                <td className="p-8 text-center" colSpan={7}>
                  <p className="font-bold text-neutral-950">
                    Không tải được danh sách chấm công
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {apiMessage(attendance.error)}
                  </p>
                  <button
                    className="mt-3 text-sm font-bold text-primary-700"
                    onClick={() => void attendance.refetch()}
                    type="button"
                  >
                    Thử lại
                  </button>
                </td>
              </tr>
            ) : null}
            {!attendance.isPending &&
            !attendance.isError &&
            rows.length === 0 ? (
              <tr>
                <td className="p-10 text-center" colSpan={7}>
                  <CalendarRange
                    aria-hidden="true"
                    className="mx-auto size-9 text-neutral-400"
                  />
                  <p className="mt-3 font-bold text-neutral-950">
                    Không có bản ghi phù hợp
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    Thử thay đổi khoảng ngày, trạng thái hoặc bộ lọc nhân viên.
                  </p>
                </td>
              </tr>
            ) : null}
            {rows.map((item) => (
              <Fragment key={item.id}>
                <tr className="border-t border-neutral-100">
                  <td className="px-5 py-4">
                    <p className="font-bold text-neutral-950">
                      {item.employeeName}
                    </p>
                    <p className="mt-1 font-mono text-xs text-neutral-500">
                      {item.employeeCode}
                    </p>
                  </td>
                  <td className="px-5 py-4 text-sm text-neutral-700">
                    {item.departmentName}
                  </td>
                  <td className="px-5 py-4 text-sm font-semibold text-neutral-800">
                    {formatDate(item.workDate)}
                  </td>
                  <td className="px-5 py-4 text-sm text-neutral-700">
                    <Clock3
                      aria-hidden="true"
                      className="mr-1 inline size-3.5 text-neutral-400"
                    />
                    {formatTime(item.checkInAt)} / {formatTime(item.checkOutAt)}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusStyles[item.status]}`}
                    >
                      {statusLabels[item.status]}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-sm text-neutral-700">
                    Muộn {item.lateMinutes}′ · Sớm {item.earlyLeaveMinutes}′
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        aria-controls={`attendance-gps-${item.id}`}
                        aria-expanded={expandedEvidenceId === item.id}
                        className="min-h-9 rounded-lg border border-emerald-300 bg-emerald-50 px-3 text-xs font-bold text-emerald-900 transition hover:bg-emerald-100"
                        onClick={() =>
                          setExpandedEvidenceId((current) =>
                            current === item.id ? null : item.id,
                          )
                        }
                        type="button"
                      >
                        {expandedEvidenceId === item.id ? "Ẩn GPS" : "Xem GPS"}
                      </button>
                      <button
                        className="min-h-9 rounded-lg border border-neutral-300 px-3 text-xs font-bold text-neutral-800 transition hover:bg-neutral-50"
                        onClick={() => beginEdit(item)}
                        type="button"
                      >
                        Điều chỉnh
                      </button>
                    </div>
                  </td>
                </tr>
                {expandedEvidenceId === item.id ? (
                  <tr className="border-t border-neutral-100">
                    <td
                      className="p-3 sm:p-5"
                      colSpan={7}
                      id={`attendance-gps-${item.id}`}
                    >
                      <AdminAttendanceLocationEvidence
                        attendanceId={item.id}
                        employeeName={item.employeeName}
                      />
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}

function EditAttendanceForm({
  attendance,
  error,
  form,
  isSaving,
  onCancel,
  onChange,
  onSubmit,
}: {
  attendance: AdminAttendance;
  error: string | null;
  form: EditForm;
  isSaving: boolean;
  onCancel: () => void;
  onChange: (field: keyof EditForm, value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form
      className="grid gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 md:grid-cols-2 xl:grid-cols-3"
      onSubmit={onSubmit}
    >
      <div className="flex items-start justify-between md:col-span-2 xl:col-span-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-emerald-800">
            Điều chỉnh có kiểm soát
          </p>
          <h2 className="mt-2 text-xl font-bold text-neutral-950">
            {attendance.employeeName} · {formatDate(attendance.workDate)}
          </h2>
          <p className="mt-1 text-sm text-neutral-600">
            Chỉ lưu dữ liệu cần thiết vào audit log; nội dung ghi chú không được
            sao chép vào log.
          </p>
        </div>
        <button
          aria-label="Đóng biểu mẫu điều chỉnh"
          className="rounded-lg p-2 text-neutral-600 hover:bg-white"
          onClick={onCancel}
          type="button"
        >
          <X className="size-5" />
        </button>
      </div>
      <label className="text-sm font-bold text-neutral-800">
        Giờ vào
        <input
          className={`${fieldClass} mt-2`}
          onChange={(event) => onChange("checkInAt", event.target.value)}
          type="datetime-local"
          value={form.checkInAt}
        />
      </label>
      <label className="text-sm font-bold text-neutral-800">
        Giờ ra
        <input
          className={`${fieldClass} mt-2`}
          onChange={(event) => onChange("checkOutAt", event.target.value)}
          type="datetime-local"
          value={form.checkOutAt}
        />
      </label>
      <label className="text-sm font-bold text-neutral-800">
        Trạng thái
        <select
          className={`${fieldClass} mt-2`}
          disabled={isLocationDecisionStatus(form.status)}
          onChange={(event) => onChange("status", event.target.value)}
          value={form.status}
        >
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {isLocationDecisionStatus(form.status) ? (
          <span className="mt-2 block text-xs font-semibold text-amber-800">
            Chỉ xử lý trạng thái này trong phần xét duyệt vị trí.
          </span>
        ) : null}
      </label>
      <label className="text-sm font-bold text-neutral-800">
        Phút đi muộn
        <input
          className={`${fieldClass} mt-2`}
          min="0"
          max="1440"
          onChange={(event) => onChange("lateMinutes", event.target.value)}
          type="number"
          value={form.lateMinutes}
        />
      </label>
      <label className="text-sm font-bold text-neutral-800">
        Phút về sớm
        <input
          className={`${fieldClass} mt-2`}
          min="0"
          max="1440"
          onChange={(event) =>
            onChange("earlyLeaveMinutes", event.target.value)
          }
          type="number"
          value={form.earlyLeaveMinutes}
        />
      </label>
      <label className="text-sm font-bold text-neutral-800 xl:col-span-3">
        Ghi chú nội bộ
        <textarea
          className={`${fieldClass} mt-2 min-h-24 py-3`}
          maxLength={2000}
          onChange={(event) => onChange("note", event.target.value)}
          value={form.note}
        />
      </label>
      {error ? (
        <p
          className="text-sm font-semibold text-red-700 md:col-span-2 xl:col-span-3"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-3 md:col-span-2 xl:col-span-3">
        <button
          className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800"
          onClick={onCancel}
          type="button"
        >
          Hủy
        </button>
        <button
          className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white disabled:opacity-50"
          disabled={isSaving}
          type="submit"
        >
          {isSaving ? "Đang lưu..." : "Lưu điều chỉnh"}
        </button>
      </div>
    </form>
  );
}
