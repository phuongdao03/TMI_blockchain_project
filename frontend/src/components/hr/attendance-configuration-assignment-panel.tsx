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
  employeeAssignments,
  employeeSearch,
  employees,
  policies,
  isSaving,
  isUpdating,
  onEmployeeSearch,
  onEmployeeSelect,
  onEndAssignment,
  onRetry,
  onRetryEmployees,
  onSave,
  selectedWorksite,
}: {
  assignments: AssignmentQuery;
  employeeAssignments: AssignmentQuery;
  employeeSearch: string;
  employees: EmployeeQuery;
  policies: AttendanceWorksitePolicy[];
  isSaving: boolean;
  isUpdating: boolean;
  onEmployeeSearch: (value: string) => void;
  onEmployeeSelect: (value: string) => void;
  onEndAssignment: (
    assignmentId: string,
    effectiveTo: string,
    reason: string,
  ) => Promise<unknown>;
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
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [transferConfirmed, setTransferConfirmed] = useState(false);
  const rows = assignments.data?.data ?? [];
  const today = new Intl.DateTimeFormat("sv-SE", {
    timeZone: policies[0]?.timezone ?? "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const currentRows = rows.filter(
    (assignment) => !assignment.effectiveTo || assignment.effectiveTo >= today,
  );
  const historyRows = rows.filter(
    (assignment) => assignment.effectiveTo && assignment.effectiveTo < today,
  );
  const selectedEmployeeAssignment = [
    ...rows,
    ...(employeeAssignments.data?.data ?? []),
  ].find((assignment) => assignment.employeeId === employeeId);
  const hasPolicy = policies.length > 0;
  const canAssign = selectedWorksite?.status === "ACTIVE" && hasPolicy;
  const conflicts = (employeeAssignments.data?.data ?? []).filter(
    (row) =>
      effectiveFrom &&
      (!row.effectiveTo || row.effectiveTo >= effectiveFrom) &&
      (!effectiveTo || row.effectiveFrom <= effectiveTo),
  );
  const transferable =
    conflicts.length === 1 && conflicts[0].effectiveFrom < effectiveFrom;
  const previousEnd = effectiveFrom
    ? new Date(Date.parse(`${effectiveFrom}T00:00:00Z`) - 86400000)
        .toISOString()
        .slice(0, 10)
    : "";

  function prepareEdit(assignment: AttendanceAssignment) {
    setShowForm(true);
    setTransferConfirmed(false);
    setEmployeeId(assignment.employeeId);
    onEmployeeSelect(assignment.employeeId);
    setWorkDays(assignment.workDays ?? [0, 1, 2, 3, 4]);
    setStartTime(assignment.startTime?.slice(0, 5) ?? "08:00");
    setEndTime(assignment.endTime?.slice(0, 5) ?? "17:00");
    setHolidayDates(assignment.holidayDates ?? []);
    setEffectiveFrom("");
    setEffectiveTo("");
    setFormError(
      "Đã điền lịch hiện tại. Kết thúc phân công cũ trước ngày hiệu lực mới, rồi lưu giai đoạn mới để giữ lịch sử.",
    );
    document.getElementById("attendance-assignment-form")?.scrollIntoView?.({
      behavior: "smooth",
    });
  }

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
      if (employeeAssignments.isPending || employeeAssignments.isError) {
        setFormError("Chờ tải đầy đủ phân công của nhân viên trước khi lưu.");
        return;
      }
      if (conflicts.length && (!transferable || !transferConfirmed)) {
        setFormError(
          "Xem phân công trùng bên dưới và xác nhận chuyển hoặc điều chỉnh ngày.",
        );
        return;
      }
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
        ...(transferable && transferConfirmed
          ? {
              replaceAssignmentId: conflicts[0].id,
              transferReason: `Chuyển phân công từ ${conflicts[0].worksiteCode} sang ${selectedWorksite.code} từ ${effectiveFrom}`,
            }
          : {}),
      });
      setEmployeeId("");
      onEmployeeSelect("");
      setEffectiveFrom("");
      setEffectiveTo("");
      setWorkDays([0, 1, 2, 3, 4]);
      setStartTime("08:00");
      setEndTime("17:00");
      setHolidayDate("");
      setHolidayDates([]);
      setShowForm(false);
      setTransferConfirmed(false);
    } catch (error) {
      setFormError(
        error instanceof ApiError &&
          error.code === "HR_ATTENDANCE_ASSIGNMENT_OVERLAP"
          ? "Có phân công khác vừa thay đổi. Tải lại danh sách bên dưới để xem văn phòng và ngày đang bị trùng."
          : error instanceof ApiError &&
              error.code === "HR_ATTENDANCE_ASSIGNMENT_HISTORY_CONFLICT"
            ? "Đã có chấm công từ ngày chuyển. Chọn ngày chuyển sau bản ghi chấm công cuối cùng; phân công cũ chưa bị thay đổi."
            : error instanceof ApiError &&
                error.code === "HR_ATTENDANCE_TRANSFER_STALE"
              ? "Phân công cũ đã thay đổi hoặc ngày chuyển chưa phù hợp. Tải lại trang để kiểm tra."
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
            Nhân viên · Văn phòng đang chọn
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

      <div className="mt-5 rounded-2xl border border-neutral-200 p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-neutral-950">
              Nhân viên tại {selectedWorksite?.name ?? "địa điểm đang chọn"}
            </h3>
            <p className="mt-1 text-sm text-neutral-600">
              {currentRows.length} phân công đang hoặc sắp có hiệu lực
            </p>
          </div>
          <button
            className="min-h-10 rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white disabled:opacity-50"
            disabled={!selectedWorksite}
            onClick={() => {
              setShowForm(true);
              setTransferConfirmed(false);
            }}
            type="button"
          >
            Thêm nhân viên
          </button>
        </div>
        {assignments.isPending ? (
          <p className="mt-3 text-sm text-neutral-600">Đang tải nhân viên...</p>
        ) : assignments.isError ? (
          <p className="mt-3 text-sm text-rose-700" role="alert">
            Không thể tải nhân viên của địa điểm.
            <button
              className="ml-2 font-bold underline"
              onClick={onRetry}
              type="button"
            >
              Thử lại
            </button>
          </p>
        ) : currentRows.length === 0 ? (
          <p className="mt-3 rounded-xl border border-dashed border-neutral-300 p-4 text-sm text-neutral-600">
            Chưa có nhân viên được phân công tại địa điểm này.
          </p>
        ) : (
          <ul className="mt-3 space-y-3" role="list">
            {currentRows.map((assignment) => (
              <li
                className="rounded-xl border border-neutral-200 p-4"
                key={assignment.id}
              >
                <p className="font-bold text-neutral-950">
                  {assignment.employeeCode} · {assignment.employeeName}
                </p>
                <p className="mt-1 text-sm text-neutral-600">
                  {assignment.workDays
                    ?.map((day) => weekdays[day])
                    .join(", ") || "Lịch cũ"}
                  {assignment.startTime && assignment.endTime
                    ? ` · ${assignment.startTime.slice(0, 5)}–${assignment.endTime.slice(0, 5)}`
                    : ""}
                  {` · ${assignment.effectiveFrom} → ${assignment.effectiveTo ?? "mở"}`}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    aria-label={`Sửa lịch ${assignment.employeeCode}`}
                    className="min-h-10 rounded-lg border border-neutral-300 px-3 text-sm font-semibold"
                    onClick={() => prepareEdit(assignment)}
                    type="button"
                  >
                    Sửa lịch
                  </button>
                  <button
                    aria-expanded={removingId === assignment.id}
                    aria-label={`Gỡ ${assignment.employeeCode} khỏi văn phòng`}
                    className="min-h-10 rounded-lg border border-rose-200 px-3 text-sm font-semibold text-rose-800"
                    onClick={() =>
                      setRemovingId((current) =>
                        current === assignment.id ? null : assignment.id,
                      )
                    }
                    type="button"
                  >
                    Gỡ khỏi văn phòng
                  </button>
                </div>
                {removingId === assignment.id ? (
                  <ul className="mt-3">
                    <EndAssignmentItem
                      assignment={assignment}
                      isUpdating={isUpdating}
                      onEnd={onEndAssignment}
                    />
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <form
        hidden={!showForm}
        className="mt-5 rounded-2xl bg-neutral-50 p-4 sm:p-5"
        id="attendance-assignment-form"
        onSubmit={submit}
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="text-lg font-bold">Thêm hoặc chuyển nhân viên</h3>
          <button
            type="button"
            onClick={() => setShowForm(false)}
            className="min-h-11 px-3 font-semibold"
          >
            Đóng biểu mẫu
          </button>
        </div>
        <label
          className="block text-sm font-semibold text-neutral-800"
          htmlFor="attendance-assignment-search"
        >
          Tìm nhân viên đang hoạt động
          <input
            className={fieldClass}
            disabled={!selectedWorksite}
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
            disabled={!selectedWorksite || employees.isPending}
            id="attendance-assignment-employee"
            onChange={(event) => {
              setEmployeeId(event.target.value);
              setTransferConfirmed(false);
              onEmployeeSelect(event.target.value);
            }}
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
            {selectedEmployeeAssignment &&
            !(employees.data?.data ?? []).some(
              (employee) => employee.id === employeeId,
            ) ? (
              <option value={selectedEmployeeAssignment.employeeId}>
                {selectedEmployeeAssignment.employeeCode} ·{" "}
                {selectedEmployeeAssignment.employeeName}
              </option>
            ) : null}
          </select>
        </label>
        <p className="mt-2 text-xs leading-5 text-neutral-600">
          Chỉ hồ sơ nhân viên đang làm việc mới xuất hiện. Nếu tài khoản chưa có
          trong danh sách, mở Nhân sự để hoàn tất hồ sơ công việc.
        </p>
        {employeeId ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/60 p-4">
            <h3 className="text-sm font-bold text-neutral-950">
              Phân công của nhân viên tại mọi địa điểm
            </h3>
            <p className="mt-1 text-sm leading-6 text-neutral-700">
                Chọn nhân viên và ngày bắt đầu để kiểm tra phân công tại mọi
                văn phòng. Có thể xác nhận chuyển sang địa điểm này; lịch sử
                chấm công vẫn được giữ.
            </p>
            {employeeAssignments.isPending ? (
              <p className="mt-3 text-sm text-neutral-600">
                Đang tải phân công...
              </p>
            ) : employeeAssignments.isError ? (
              <p className="mt-3 text-sm text-rose-700" role="alert">
                Không thể tải phân công của nhân viên.
              </p>
            ) : (employeeAssignments.data?.data.length ?? 0) === 0 ? (
              <p className="mt-3 text-sm text-neutral-600">
                Nhân viên chưa có phân công.
              </p>
            ) : (
              <details className="mt-3 rounded-xl border border-amber-200 bg-white p-3">
                <summary className="cursor-pointer text-sm font-semibold">
                  Xem và chỉnh {employeeAssignments.data?.meta.total ?? 0} phân
                  công tại mọi địa điểm
                </summary>
                <ul className="mt-3 space-y-3">
                  {employeeAssignments.data?.data.map((assignment) => (
                    <EndAssignmentItem
                      assignment={assignment}
                      isUpdating={isUpdating}
                      key={assignment.id}
                      onEnd={onEndAssignment}
                    />
                  ))}
                </ul>
              </details>
            )}
          </div>
        ) : null}
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
              onChange={(event) => {
                setEffectiveFrom(event.target.value);
                setTransferConfirmed(false);
              }}
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
              onChange={(event) => {
                setEffectiveTo(event.target.value);
                setTransferConfirmed(false);
              }}
              type="date"
              value={effectiveTo}
            />
          </label>
          {conflicts.length > 0 ? (
            <div
              role="status"
              className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
            >
              <p className="font-bold">
                Phân công đang trùng với thời gian đã chọn
              </p>
              <ul className="mt-2 space-y-2">
                {conflicts.map((row) => (
                  <li key={row.id}>
                    <strong>
                      {row.worksiteCode} · {row.worksiteName}
                    </strong>
                    <br />
                    {row.effectiveFrom} → {row.effectiveTo ?? "Chưa kết thúc"}
                  </li>
                ))}
              </ul>
              {transferable ? (
                <label className="mt-3 flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1 size-5"
                    checked={transferConfirmed}
                    onChange={(event) =>
                      setTransferConfirmed(event.target.checked)
                    }
                  />
                  <span>
                    Kết thúc phân công tại {conflicts[0].worksiteCode} ngày{" "}
                    {previousEnd} và chuyển sang {selectedWorksite?.code} từ{" "}
                    {effectiveFrom}. Giữ lịch sử chấm công.
                  </span>
                </label>
              ) : (
                <p className="mt-3">
                  Chọn ngày bắt đầu sau ngày bắt đầu phân công cũ, hoặc điều
                  chỉnh từng phân công trong danh sách ở trên.
                </p>
              )}
            </div>
          ) : null}
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
            {formError.includes("Tải lại danh sách") ? (
              <button
                className="font-bold underline"
                onClick={onRetry}
                type="button"
              >
                Tải lại phân công
              </button>
            ) : null}
          </p>
        ) : null}
        <button
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={
            isSaving ||
            !canAssign ||
            (!!employeeId &&
              (employeeAssignments.isPending || employeeAssignments.isError))
          }
          type="submit"
        >
          {isSaving
            ? "Đang lưu..."
            : transferConfirmed && transferable
              ? "Xác nhận chuyển và lưu"
              : "Lưu phân công"}
        </button>
      </form>

      {historyRows.length > 0 ? (
        <details className="mt-5 rounded-xl border border-neutral-200 p-4">
          <summary className="cursor-pointer text-sm font-bold text-neutral-800">
            Lịch sử phân công · {historyRows.length} bản ghi
          </summary>
          <ul className="mt-3 grid gap-3 sm:grid-cols-2" role="list">
            {historyRows.map((assignment) => (
              <AssignmentHistoryItem
                assignment={assignment}
                key={assignment.id}
              />
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function EndAssignmentItem({
  assignment,
  isUpdating,
  onEnd,
}: {
  assignment: AttendanceAssignment;
  isUpdating: boolean;
  onEnd: (
    assignmentId: string,
    effectiveTo: string,
    reason: string,
  ) => Promise<unknown>;
}) {
  const [effectiveTo, setEffectiveTo] = useState(assignment.effectiveTo ?? "");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const label = assignment.worksiteCode;

  async function saveEnd() {
    setError(null);
    if (!effectiveTo || effectiveTo < assignment.effectiveFrom) {
      setError("Ngày kết thúc phải từ ngày bắt đầu phân công trở đi.");
      return;
    }
    if (reason.trim().length < 10) {
      setError("Nhập lý do điều chỉnh ít nhất 10 ký tự.");
      return;
    }
    try {
      await onEnd(assignment.id, effectiveTo, reason.trim());
      setReason("");
    } catch (cause) {
      setError(
        cause instanceof ApiError &&
          cause.code === "HR_ATTENDANCE_ASSIGNMENT_HISTORY_CONFLICT"
          ? "Ngày kết thúc đang trước một bản ghi chấm công đã có. Chọn ngày sau bản ghi đó."
          : cause instanceof ApiError &&
              cause.code === "HR_ATTENDANCE_ASSIGNMENT_OVERLAP"
            ? "Ngày kết thúc đang trùng với phân công khác của nhân viên."
            : "Không thể điều chỉnh phân công. Kiểm tra ngày và thử lại.",
      );
    }
  }

  return (
    <li className="rounded-xl border border-amber-200 bg-white p-4">
      <p className="text-sm font-bold text-neutral-950">
        {assignment.worksiteCode} · {assignment.worksiteName}
      </p>
      <p className="mt-1 text-xs text-neutral-600">
        Hiệu lực {assignment.effectiveFrom} →{" "}
        {assignment.effectiveTo ?? "đang mở"}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-semibold text-neutral-800">
          Ngày kết thúc phân công {label}
          <input
            className={fieldClass}
            min={assignment.effectiveFrom}
            onChange={(event) => setEffectiveTo(event.target.value)}
            type="date"
            value={effectiveTo}
          />
        </label>
        <label className="text-sm font-semibold text-neutral-800">
          Lý do điều chỉnh phân công {label}
          <input
            className={fieldClass}
            maxLength={500}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Ví dụ: Chuyển sang địa điểm mới"
            type="text"
            value={reason}
          />
        </label>
      </div>
      {error ? (
        <p className="mt-2 text-sm text-rose-700" role="alert">
          {error}
        </p>
      ) : null}
      <button
        className="mt-3 min-h-11 rounded-xl border border-amber-500 bg-white px-4 text-sm font-bold text-amber-950 disabled:opacity-50"
        disabled={
          isUpdating ||
          !effectiveTo ||
          reason.trim().length < 10 ||
          effectiveTo === assignment.effectiveTo
        }
        onClick={() => void saveEnd()}
        type="button"
      >
        {assignment.effectiveTo
          ? `Điều chỉnh ngày kết thúc ${label}`
          : `Kết thúc phân công ${label}`}
      </button>
    </li>
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
