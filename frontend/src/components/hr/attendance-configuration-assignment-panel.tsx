"use client";

import { CircleAlert, UserRoundCheck, UsersRound } from "lucide-react";
import { type FormEvent, useState } from "react";

import type {
  AttendanceAssignment,
  AttendanceWorksite,
  Employee,
} from "@/lib/api/types";

import type { AssignmentInput } from "./attendance-configuration-types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-neutral-100";

type AssignmentQuery = {
  data?: { data: AttendanceAssignment[]; meta: { total: number } };
  isPending: boolean;
  isError: boolean;
};
type EmployeeQuery = {
  data?: { data: Employee[] };
  isPending: boolean;
};

export function AttendanceAssignmentPanel({
  assignments,
  employeeSearch,
  employees,
  isSaving,
  onEmployeeSearch,
  onRetry,
  onSave,
  selectedWorksite,
}: {
  assignments: AssignmentQuery;
  employeeSearch: string;
  employees: EmployeeQuery;
  isSaving: boolean;
  onEmployeeSearch: (value: string) => void;
  onRetry: () => void;
  onSave: (input: AssignmentInput) => Promise<unknown>;
  selectedWorksite: AttendanceWorksite | null;
}) {
  const [employeeId, setEmployeeId] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [scheduleCode, setScheduleCode] = useState("");
  const [holidayCalendarCode, setHolidayCalendarCode] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const rows = assignments.data?.data ?? [];
  const canAssign = selectedWorksite?.status === "ACTIVE";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (
      !canAssign ||
      !employeeId ||
      !effectiveFrom ||
      !scheduleCode.trim() ||
      !holidayCalendarCode.trim()
    ) {
      setFormError("Chọn nhân viên và nhập đầy đủ lịch làm việc, lịch nghỉ.");
      return;
    }
    if (effectiveTo && effectiveTo < effectiveFrom) {
      setFormError("Ngày kết thúc không được trước ngày hiệu lực.");
      return;
    }
    try {
      await onSave({
        employeeId,
        worksiteId: selectedWorksite.id,
        effectiveFrom,
        effectiveTo: effectiveTo || null,
        scheduleCode: scheduleCode.trim(),
        holidayCalendarCode: holidayCalendarCode.trim(),
      });
      setEmployeeId("");
      setEffectiveFrom("");
      setEffectiveTo("");
      setScheduleCode("");
      setHolidayCalendarCode("");
    } catch {
      setFormError(
        "Không thể lưu phân công. Có thể nhân viên đã có lịch hiệu lực chồng lấn.",
      );
    }
  }

  return (
    <section
      aria-labelledby="attendance-assignment-title"
      className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm sm:p-6"
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
          <UsersRound aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">
            03 · Phân công
          </p>
          <h2
            className="mt-1 text-xl font-bold text-neutral-950"
            id="attendance-assignment-title"
          >
            Lịch làm việc của nhân viên
          </h2>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Gán đúng địa điểm, lịch làm và lịch nghỉ cho từng giai đoạn.
          </p>
        </div>
      </div>

      <form
        className="mt-5 rounded-2xl bg-neutral-50 p-4 sm:p-5"
        onSubmit={submit}
      >
        <label
          className="block text-sm font-semibold text-neutral-800"
          htmlFor="attendance-assignment-search"
        >
          Tìm nhân viên đang hoạt động
          <input
            className={fieldClass}
            disabled={!canAssign}
            id="attendance-assignment-search"
            onChange={(event) => onEmployeeSearch(event.target.value)}
            placeholder="Mã, tên hoặc email"
            value={employeeSearch}
          />
        </label>
        <label
          className="mt-3 block text-sm font-semibold text-neutral-800"
          htmlFor="attendance-assignment-employee"
        >
          Nhân viên
          <select
            className={fieldClass}
            disabled={!canAssign || employees.isPending}
            id="attendance-assignment-employee"
            onChange={(event) => setEmployeeId(event.target.value)}
            value={employeeId}
          >
            <option value="">
              {employees.isPending ? "Đang tìm..." : "Chọn nhân viên"}
            </option>
            {(employees.data?.data ?? []).map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.employeeCode} · {employee.fullName}
              </option>
            ))}
          </select>
        </label>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-assignment-effective-from"
          >
            Ngày hiệu lực phân công
            <input
              className={fieldClass}
              disabled={!canAssign}
              id="attendance-assignment-effective-from"
              onChange={(event) => setEffectiveFrom(event.target.value)}
              type="date"
              value={effectiveFrom}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-assignment-effective-to"
          >
            Kết thúc{" "}
            <span className="font-normal text-neutral-500">(nếu có)</span>
            <input
              className={fieldClass}
              disabled={!canAssign}
              id="attendance-assignment-effective-to"
              min={effectiveFrom || undefined}
              onChange={(event) => setEffectiveTo(event.target.value)}
              type="date"
              value={effectiveTo}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-assignment-schedule"
          >
            Mã lịch làm việc
            <input
              className={fieldClass}
              disabled={!canAssign}
              id="attendance-assignment-schedule"
              maxLength={64}
              onChange={(event) => setScheduleCode(event.target.value)}
              placeholder="VD: MON_FRI_8H"
              value={scheduleCode}
            />
          </label>
          <label
            className="block text-sm font-semibold text-neutral-800"
            htmlFor="attendance-assignment-holiday-calendar"
          >
            Mã lịch nghỉ lễ
            <input
              className={fieldClass}
              disabled={!canAssign}
              id="attendance-assignment-holiday-calendar"
              maxLength={64}
              onChange={(event) => setHolidayCalendarCode(event.target.value)}
              placeholder="VD: VN-HCM"
              value={holidayCalendarCode}
            />
          </label>
        </div>
        {selectedWorksite && !canAssign ? (
          <p className="mt-3 text-sm text-amber-800">
            Địa điểm đang tạm ngưng nên chưa thể phân công mới.
          </p>
        ) : null}
        {formError ? (
          <p className="mt-3 flex gap-2 text-sm text-rose-700" role="alert">
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            {formError}
          </p>
        ) : null}
        <button
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSaving || !canAssign}
          type="submit"
        >
          {isSaving ? "Đang lưu..." : "Lưu phân công"}
        </button>
      </form>

      <div className="mt-5" aria-live="polite">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-neutral-950">
            Phân công đã ghi nhận
          </h3>
          <span className="text-xs font-semibold text-neutral-500">
            {assignments.data?.meta.total ?? 0} bản ghi
          </span>
        </div>
        {assignments.isPending ? (
          <div
            aria-busy="true"
            className="mt-3 h-24 animate-pulse rounded-xl bg-neutral-100"
          />
        ) : null}
        {assignments.isError ? (
          <p
            className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
            role="alert"
          >
            Không thể tải phân công.
            <button
              className="ml-2 font-bold underline"
              onClick={onRetry}
              type="button"
            >
              Thử lại
            </button>
          </p>
        ) : null}
        {!assignments.isPending && !assignments.isError && rows.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-neutral-300 p-4 text-sm leading-6 text-neutral-600">
            Chưa có phân công. Chỉ gán sau khi chính sách GPS của địa điểm đã
            được thiết lập.
          </p>
        ) : null}
        <ul className="mt-3 grid gap-3 sm:grid-cols-2" role="list">
          {rows.map((assignment) => (
            <AssignmentHistoryItem
              assignment={assignment}
              key={assignment.id}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}

function AssignmentHistoryItem({
  assignment,
}: {
  assignment: AttendanceAssignment;
}) {
  return (
    <li className="rounded-xl border border-neutral-200 p-4">
      <p className="flex items-center gap-2 text-sm font-bold text-neutral-950">
        <UserRoundCheck
          aria-hidden="true"
          className="size-4 text-emerald-700"
        />
        {assignment.employeeName}
      </p>
      <p className="mt-1 text-xs font-bold tracking-wide text-neutral-500">
        {assignment.employeeCode} · {assignment.worksiteCode}
      </p>
      <dl className="mt-3 grid gap-2 text-sm text-neutral-600">
        <div className="flex justify-between gap-3">
          <dt>Lịch làm</dt>
          <dd className="font-semibold text-neutral-900">
            {assignment.scheduleCode}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Hiệu lực</dt>
          <dd className="text-right">
            {assignment.effectiveFrom}
            {assignment.effectiveTo ? ` → ${assignment.effectiveTo}` : " → mở"}
          </dd>
        </div>
      </dl>
    </li>
  );
}
