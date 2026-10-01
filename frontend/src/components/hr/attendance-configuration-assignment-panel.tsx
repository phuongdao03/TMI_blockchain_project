"use client";

import { CircleAlert, UserRoundCheck, UsersRound } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { ApiError } from "@/lib/api/client";
import type {
  AttendanceAssignment,
  AttendanceWorksite,
  AttendanceWorksitePolicy,
  Employee,
} from "@/lib/api/types";

import type { AssignmentInput } from "./attendance-configuration-types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-neutral-100";
const weekdays = [
  "Thứ 2",
  "Thứ 3",
  "Thứ 4",
  "Thứ 5",
  "Thứ 6",
  "Thứ 7",
  "Chủ nhật",
];

type AssignmentQuery = {
  data?: { data: AttendanceAssignment[]; meta: { total: number } };
  isPending: boolean;
  isError: boolean;
};
type EmployeeQuery = {
  data?: { data: Employee[] };
  isPending: boolean;
  isError: boolean;
};

export function AttendanceAssignmentPanel({
  assignments,
  employeeSearch,
  employees,
  policies,
  isSaving,
  onEmployeeSearch,
  onRetry,
  onRetryEmployees,
  onSave,
  selectedWorksite,
}: {
  assignments: AssignmentQuery;
  employeeSearch: string;
  employees: EmployeeQuery;
  policies: AttendanceWorksitePolicy[];
  isSaving: boolean;
  onEmployeeSearch: (value: string) => void;
  onRetry: () => void;
  onRetryEmployees: () => void;
  onSave: (input: AssignmentInput) => Promise<unknown>;
  selectedWorksite: AttendanceWorksite | null;
}) {
  const [employeeId, setEmployeeId] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [workDays, setWorkDays] = useState([0, 1, 2, 3, 4]);
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("17:00");
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayDates, setHolidayDates] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const rows = assignments.data?.data ?? [];
  const hasPolicy = policies.length > 0;
  const canAssign = selectedWorksite?.status === "ACTIVE" && hasPolicy;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (
      !canAssign ||
      !employeeId ||
      !effectiveFrom ||
      workDays.length === 0 ||
      !startTime ||
      !endTime
    ) {
      setFormError(
        "Chọn nhân viên, ít nhất một ngày làm việc và giờ bắt đầu/kết thúc.",
      );
      return;
    }
    if (endTime <= startTime) {
      setFormError("Giờ kết thúc phải sau giờ bắt đầu.");
      return;
    }
    if (effectiveTo && effectiveTo < effectiveFrom) {
      setFormError("Ngày kết thúc không được trước ngày hiệu lực.");
      return;
    }
    if (
      !policies.some(
        (policy) =>
          policy.effectiveFrom <= effectiveFrom &&
          (!policy.effectiveTo || policy.effectiveTo >= effectiveFrom),
      )
    ) {
      setFormError(
        "Ngày phân công phải nằm trong thời gian hiệu lực của vùng chấm công.",
      );
      return;
    }
    try {
      await onSave({
        employeeId,
        worksiteId: selectedWorksite.id,
        effectiveFrom,
        effectiveTo: effectiveTo || null,
        scheduleCode: "CUSTOM",
        holidayCalendarCode: "CUSTOM",
        workDays,
        startTime,
        endTime,
        holidayDates,
      });
      setEmployeeId("");
      setEffectiveFrom("");
      setEffectiveTo("");
      setWorkDays([0, 1, 2, 3, 4]);
      setStartTime("08:00");
      setEndTime("17:00");
      setHolidayDate("");
      setHolidayDates([]);
    } catch (error) {
      setFormError(
        error instanceof ApiError &&
          error.code === "HR_ATTENDANCE_ASSIGNMENT_OVERLAP"
          ? "Nhân viên đã có phân công trong khoảng thời gian này. Chọn giai đoạn khác."
          : error instanceof ApiError &&
              error.code === "HR_ATTENDANCE_ASSIGNMENT_POLICY_REQUIRED"
            ? "Ngày phân công chưa có vùng chấm công hiệu lực. Kiểm tra lại chính sách."
            : "Không thể lưu phân công. Kiểm tra dữ liệu và thử lại.",
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
            Chọn nhân viên, ngày làm việc và giờ làm tại địa điểm này. Tài khoản
            cần có hồ sơ nhân viên liên kết trước khi chấm công.
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
        {employees.isError ? (
          <p className="mt-3 text-sm text-rose-700" role="alert">
            Không tải được danh sách nhân viên.
            <button
              className="ml-2 font-semibold underline"
              onClick={onRetryEmployees}
              type="button"
            >
              Thử lại
            </button>
          </p>
        ) : null}
        {!employees.isPending &&
        !employees.isError &&
        (employees.data?.data.length ?? 0) === 0 ? (
          <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
            {employeeSearch.trim()
              ? "Không thấy hồ sơ nhân viên đang làm việc với từ khóa này. Nếu đây là tài khoản vừa được mời, hãy tạo hồ sơ và liên kết tài khoản trong Nhân sự."
              : "Chưa có hồ sơ nhân viên đang làm việc. Mời tài khoản chỉ cấp quyền đăng nhập; để chấm công, cần tạo hồ sơ nhân viên và liên kết tài khoản."}{" "}
            <Link
              className="font-bold underline"
              href={`/admin/employees?view=employees${employeeSearch.trim().includes("@") ? `&account=${encodeURIComponent(employeeSearch.trim())}` : ""}`}
            >
              Tạo hoặc liên kết hồ sơ nhân viên
            </Link>
          </p>
        ) : null}
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
        <p className="mt-2 text-xs leading-5 text-neutral-600">
          Chỉ hồ sơ nhân viên đang làm việc mới xuất hiện. Nếu tài khoản chưa có
          trong danh sách, mở Nhân sự để hoàn tất hồ sơ công việc.
        </p>
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
          <fieldset className="sm:col-span-2">
            <legend className="text-sm font-semibold text-neutral-800">
              Ngày làm việc hằng tuần
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {weekdays.map((label, day) => (
                <label
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-sm font-semibold transition ${workDays.includes(day) ? "border-emerald-700 bg-emerald-700 text-white" : "border-neutral-300 bg-white text-neutral-700"}`}
                  key={day}
                >
                  <input
                    checked={workDays.includes(day)}
                    className="sr-only"
                    disabled={!canAssign}
                    onChange={() =>
                      setWorkDays((current) =>
                        current.includes(day)
                          ? current.filter((value) => value !== day)
                          : [...current, day].sort(),
                      )
                    }
                    type="checkbox"
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="text-sm font-semibold text-neutral-800">
            Giờ bắt đầu
            <input
              className={fieldClass}
              disabled={!canAssign}
              onChange={(event) => setStartTime(event.target.value)}
              required
              type="time"
              value={startTime}
            />
          </label>
          <label className="text-sm font-semibold text-neutral-800">
            Giờ kết thúc
            <input
              className={fieldClass}
              disabled={!canAssign}
              min={startTime}
              onChange={(event) => setEndTime(event.target.value)}
              required
              type="time"
              value={endTime}
            />
          </label>
          <div className="sm:col-span-2">
            <label
              className="block text-sm font-semibold text-neutral-800"
              htmlFor="attendance-holiday-date"
            >
              Ngày nghỉ lễ riêng (nếu có)
            </label>
            <div className="flex flex-wrap items-end gap-2">
              <input
                className={`${fieldClass} max-w-64`}
                disabled={!canAssign}
                id="attendance-holiday-date"
                onChange={(event) => setHolidayDate(event.target.value)}
                type="date"
                value={holidayDate}
              />
              <button
                className="min-h-11 rounded-xl border border-neutral-300 bg-white px-4 text-sm font-semibold text-neutral-800"
                disabled={!holidayDate || holidayDates.includes(holidayDate)}
                onClick={() => {
                  setHolidayDates((current) =>
                    [...current, holidayDate].sort(),
                  );
                  setHolidayDate("");
                }}
                type="button"
              >
                Thêm ngày nghỉ
              </button>
            </div>
            {holidayDates.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {holidayDates.map((day) => (
                  <li
                    className="rounded-lg bg-neutral-200 px-3 py-1 text-sm text-neutral-900"
                    key={day}
                  >
                    {day}{" "}
                    <button
                      aria-label={`Bỏ ngày nghỉ ${day}`}
                      className="ml-1 font-bold"
                      onClick={() =>
                        setHolidayDates((current) =>
                          current.filter((value) => value !== day),
                        )
                      }
                      type="button"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-xs text-neutral-600">
                Không chọn nếu chưa có ngày nghỉ riêng.
              </p>
            )}
          </div>
        </div>
        {selectedWorksite && !canAssign ? (
          <p className="mt-3 text-sm text-amber-800">
            {selectedWorksite.status !== "ACTIVE"
              ? "Địa điểm đang tạm ngưng nên chưa thể phân công mới."
              : "Lưu vùng chấm công trước khi phân công nhân viên."}
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
            {assignment.workDays?.length &&
            assignment.startTime &&
            assignment.endTime
              ? `${assignment.workDays.map((day) => weekdays[day]).join(", ")} · ${assignment.startTime.slice(0, 5)}–${assignment.endTime.slice(0, 5)}`
              : `Lịch cũ: ${assignment.scheduleCode}`}
          </dd>
        </div>
        {assignment.holidayDates?.length ? (
          <div className="flex justify-between gap-3">
            <dt>Nghỉ lễ</dt>
            <dd className="text-right">{assignment.holidayDates.join(", ")}</dd>
          </div>
        ) : null}
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
