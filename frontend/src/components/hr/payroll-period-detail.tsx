"use client";

import {
  Calculator,
  CircleAlert,
  Edit3,
  LockKeyhole,
  ReceiptText,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  formatPayrollMonth,
  formatTimestamp,
  formatVnd,
  payrollApiMessage,
  payrollStatusLabels,
  payrollStatusTones,
} from "@/components/hr/payroll-format";
import type { PayrollEntry, PayrollPeriodDetail } from "@/lib/api/types";

const amountFieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100";

type EntryAdjustment = {
  allowance: string;
  socialInsurance: string;
  incomeTax: string;
};
type PendingAction = "confirm" | "paid" | null;

function detailsFor(entry: PayrollEntry) {
  return [
    { label: "Lương cơ bản", value: formatVnd(entry.baseSalary) },
    { label: "Ngày công", value: entry.attendanceWorkdays },
    { label: "Giờ OT đã duyệt", value: entry.approvedOvertimeHours },
    { label: "Phụ cấp", value: formatVnd(entry.allowance) },
    { label: "Khấu trừ", value: formatVnd(entry.totalDeductions) },
  ];
}

function entryAdjustment(entry: PayrollEntry): EntryAdjustment {
  return {
    allowance: entry.allowance,
    socialInsurance: entry.socialInsurance,
    incomeTax: entry.incomeTax,
  };
}

function PayrollEntryCard({
  entry,
  editable,
  onEdit,
}: {
  entry: PayrollEntry;
  editable: boolean;
  onEdit: (entry: PayrollEntry) => void;
}) {
  return (
    <article className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-bold text-neutral-950">{entry.employeeName}</h3>
          <p className="mt-1 text-xs font-semibold text-neutral-500">
            {entry.employeeCode}
          </p>
        </div>
        {editable ? (
          <button
            className="min-h-10 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800"
            onClick={() => onEdit(entry)}
            type="button"
          >
            Điều chỉnh
          </button>
        ) : null}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        {detailsFor(entry).map((item) => (
          <div key={item.label}>
            <dt className="text-neutral-500">{item.label}</dt>
            <dd className="mt-1 font-semibold text-neutral-900">
              {item.value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 border-t border-neutral-100 pt-3">
        <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">
          Thực lĩnh
        </p>
        <p className="mt-1 font-mono text-lg font-bold text-emerald-800">
          {formatVnd(entry.netPay)}
        </p>
      </div>
    </article>
  );
}

function EntryAdjustmentForm({
  entry,
  isSaving,
  onCancel,
  onSave,
}: {
  entry: PayrollEntry;
  isSaving: boolean;
  onCancel: () => void;
  onSave: (entryId: string, values: EntryAdjustment) => Promise<void>;
}) {
  const [values, setValues] = useState<EntryAdjustment>(() =>
    entryAdjustment(entry),
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setErrorMessage(null);
      await onSave(entry.id, values);
      onCancel();
    } catch (error) {
      setErrorMessage(payrollApiMessage(error));
    }
  }

  return (
    <form
      className="rounded-2xl border border-primary-200 bg-primary-50/60 p-5"
      onSubmit={submit}
    >
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-bold text-neutral-950">
            Điều chỉnh đầu vào
          </h3>
          <p className="mt-1 text-sm text-neutral-600">
            {entry.employeeName} ({entry.employeeCode})
          </p>
        </div>
        <span className="text-xs font-semibold text-neutral-600">
          Đơn vị VND
        </span>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <label className="text-sm font-bold text-neutral-800">
          Phụ cấp
          <input
            className={amountFieldClass}
            min="0"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                allowance: event.target.value,
              }))
            }
            required
            step="1"
            type="number"
            value={values.allowance}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800">
          BHXH
          <input
            className={amountFieldClass}
            min="0"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                socialInsurance: event.target.value,
              }))
            }
            required
            step="1"
            type="number"
            value={values.socialInsurance}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800">
          Thuế TNCN
          <input
            className={amountFieldClass}
            min="0"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                incomeTax: event.target.value,
              }))
            }
            required
            step="1"
            type="number"
            value={values.incomeTax}
          />
        </label>
      </div>
      {errorMessage ? (
        <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
          {errorMessage}
        </p>
      ) : null}
      <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800"
          disabled={isSaving}
          onClick={onCancel}
          type="button"
        >
          Hủy
        </button>
        <button
          className="min-h-11 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
          disabled={isSaving}
          type="submit"
        >
          {isSaving ? "Đang lưu..." : "Lưu đầu vào"}
        </button>
      </div>
    </form>
  );
}

function EmptyEntries() {
  return (
    <div className="p-8 text-center">
      <ReceiptText
        aria-hidden="true"
        className="mx-auto size-8 text-neutral-400"
      />
      <p className="mt-3 font-bold text-neutral-950">Chưa có dòng lương</p>
      <p className="mt-1 text-sm text-neutral-600">
        Tính lại số liệu sau khi hoàn tất phân công địa điểm và chấm công.
      </p>
    </div>
  );
}

function PayrollEntryTable({
  entries,
  editable,
  onEdit,
}: {
  entries: PayrollEntry[];
  editable: boolean;
  onEdit: (entry: PayrollEntry) => void;
}) {
  return (
    <div className="hidden overflow-x-auto sm:block">
      <table className="min-w-[980px] w-full text-left">
        <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
          <tr>
            <th className="px-5 py-3">Nhân viên</th>
            <th className="px-5 py-3 text-right">Lương cơ bản</th>
            <th className="px-5 py-3 text-right">Công và OT</th>
            <th className="px-5 py-3 text-right">Phụ cấp</th>
            <th className="px-5 py-3 text-right">Khấu trừ</th>
            <th className="px-5 py-3 text-right">Thực lĩnh</th>
            <th className="px-5 py-3">
              <span className="sr-only">Điều chỉnh</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr className="border-t border-neutral-100" key={entry.id}>
              <td className="px-5 py-4">
                <p className="font-bold text-neutral-950">
                  {entry.employeeName}
                </p>
                <p className="mt-1 text-xs font-semibold text-neutral-500">
                  {entry.employeeCode}
                </p>
              </td>
              <td className="px-5 py-4 text-right font-mono text-sm font-semibold text-neutral-800">
                {formatVnd(entry.baseSalary)}
              </td>
              <td className="px-5 py-4 text-right text-sm text-neutral-700">
                <p>{entry.attendanceWorkdays} ngày</p>
                <p className="mt-1 text-xs text-neutral-500">
                  {entry.approvedOvertimeHours} giờ OT
                </p>
              </td>
              <td className="px-5 py-4 text-right font-mono text-sm text-neutral-700">
                {formatVnd(entry.allowance)}
              </td>
              <td className="px-5 py-4 text-right font-mono text-sm text-neutral-700">
                {formatVnd(entry.totalDeductions)}
              </td>
              <td className="px-5 py-4 text-right font-mono text-sm font-bold text-emerald-800">
                {formatVnd(entry.netPay)}
              </td>
              <td className="px-5 py-4 text-right">
                {editable ? (
                  <button
                    className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 hover:bg-neutral-50"
                    onClick={() => onEdit(entry)}
                    type="button"
                  >
                    <Edit3 aria-hidden="true" className="size-4" />
                    Điều chỉnh
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PayrollPeriodDetail({
  period,
  worksiteName,
  isLoading,
  errorMessage,
  onRetry,
  onRecalculate,
  onConfirm,
  onMarkPaid,
  onUpdateEntry,
}: {
  period: PayrollPeriodDetail | undefined;
  worksiteName: string | undefined;
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onRecalculate: () => Promise<void>;
  onConfirm: () => Promise<void>;
  onMarkPaid: () => Promise<void>;
  onUpdateEntry: (entryId: string, values: EntryAdjustment) => Promise<void>;
}) {
  const [editingEntry, setEditingEntry] = useState<PayrollEntry | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (isLoading)
    return (
      <div
        className="h-96 animate-pulse rounded-2xl bg-neutral-100"
        aria-label="Đang tải chi tiết kỳ lương"
      />
    );
  if (errorMessage)
    return (
      <section
        className="rounded-2xl border border-red-200 bg-red-50 p-5"
        role="alert"
      >
        <h2 className="font-bold text-red-950">
          Không tải được chi tiết kỳ lương
        </h2>
        <p className="mt-1 text-sm text-red-800">{errorMessage}</p>
        <button
          className="mt-4 min-h-10 rounded-lg bg-white px-3 text-sm font-bold text-red-900 shadow-sm"
          onClick={onRetry}
          type="button"
        >
          Thử lại
        </button>
      </section>
    );
  if (!period) return null;

  const editable = period.status === "DRAFT";
  const actionLabel =
    pendingAction === "confirm" ? "Xác nhận số liệu" : "Đánh dấu đã chi";
  const actionDescription =
    pendingAction === "confirm"
      ? "Kỳ lương sẽ được khóa. Các đầu vào và kết quả sẽ không thể sửa trong Payroll V1."
      : "Thao tác này chỉ ghi nhận trạng thái đã chi nội bộ, không tạo lệnh thanh toán ngân hàng.";

  async function recalculate() {
    try {
      setActionError(null);
      setIsWorking(true);
      await onRecalculate();
    } catch (error) {
      setActionError(payrollApiMessage(error));
    } finally {
      setIsWorking(false);
    }
  }
  async function completeAction() {
    if (!pendingAction) return;
    try {
      setActionError(null);
      setIsWorking(true);
      if (pendingAction === "confirm") await onConfirm();
      else await onMarkPaid();
      setPendingAction(null);
    } catch (error) {
      setActionError(payrollApiMessage(error));
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <section
      aria-labelledby="payroll-period-detail-title"
      className="space-y-5"
    >
      <header className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm font-semibold text-neutral-500">
                {worksiteName ?? "Địa điểm đã lưu"}
              </p>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-bold ${payrollStatusTones[period.status]}`}
              >
                {payrollStatusLabels[period.status]}
              </span>
            </div>
            <h2
              className="mt-2 text-2xl font-bold tracking-tight text-neutral-950"
              id="payroll-period-detail-title"
            >
              {formatPayrollMonth(period.periodMonth)}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
              {period.standardWorkdays} ngày công chuẩn. Tính từ chấm công hợp
              lệ và tăng ca đã được duyệt.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
            {editable ? (
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isWorking}
                onClick={() => void recalculate()}
                type="button"
              >
                <Calculator aria-hidden="true" className="size-4" />
                {isWorking ? "Đang tính..." : "Tính lại số liệu"}
              </button>
            ) : null}
            {period.status === "DRAFT" ? (
              <button
                className="min-h-11 rounded-xl border border-primary-700 px-4 text-sm font-bold text-primary-800 disabled:cursor-not-allowed disabled:opacity-45"
                disabled={!period.calculatedAt || isWorking}
                onClick={() => setPendingAction("confirm")}
                type="button"
              >
                Xác nhận số liệu
              </button>
            ) : null}
            {period.status === "CONFIRMED" ? (
              <button
                className="min-h-11 rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isWorking}
                onClick={() => setPendingAction("paid")}
                type="button"
              >
                Đánh dấu đã chi
              </button>
            ) : null}
          </div>
        </div>
        <dl className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-neutral-50 p-4">
            <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
              Nhân viên
            </dt>
            <dd className="mt-2 text-xl font-bold text-neutral-950">
              {period.entries.length}
            </dd>
          </div>
          <div className="rounded-xl bg-neutral-50 p-4">
            <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
              Tính gần nhất
            </dt>
            <dd className="mt-2 text-sm font-semibold text-neutral-900">
              {formatTimestamp(period.calculatedAt)}
            </dd>
          </div>
          <div className="rounded-xl bg-neutral-50 p-4">
            <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
              Đơn vị tiền
            </dt>
            <dd className="mt-2 text-xl font-bold text-neutral-950">VND</dd>
          </div>
        </dl>
        {editable && !period.calculatedAt ? (
          <p className="mt-4 flex gap-2 rounded-xl bg-amber-50 px-3 py-3 text-sm leading-5 text-amber-900">
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            Tính lại số liệu trước khi xác nhận. Hệ thống chỉ dùng ngày công hợp
            lệ và tăng ca đã được duyệt.
          </p>
        ) : null}
        {!editable ? (
          <p className="mt-4 flex gap-2 rounded-xl bg-neutral-100 px-3 py-3 text-sm leading-5 text-neutral-700">
            <LockKeyhole
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            Kỳ lương đã được khóa. Payroll V1 không cho phép ghi đè số liệu đã
            xác nhận hoặc đã chi.
          </p>
        ) : null}
        {actionError ? (
          <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
            {actionError}
          </p>
        ) : null}
      </header>
      {pendingAction ? (
        <section
          className="rounded-2xl border border-primary-200 bg-primary-50/60 p-5"
          aria-labelledby="payroll-action-title"
        >
          <h3
            className="text-base font-bold text-neutral-950"
            id="payroll-action-title"
          >
            {actionLabel}
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-700">
            {actionDescription}
          </p>
          <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              className="min-h-11 rounded-xl border border-neutral-300 bg-white px-5 text-sm font-bold text-neutral-800"
              disabled={isWorking}
              onClick={() => setPendingAction(null)}
              type="button"
            >
              Hủy
            </button>
            <button
              className="min-h-11 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isWorking}
              onClick={() => void completeAction()}
              type="button"
            >
              {isWorking ? "Đang xử lý..." : actionLabel}
            </button>
          </div>
        </section>
      ) : null}
      {editingEntry ? (
        <EntryAdjustmentForm
          entry={editingEntry}
          isSaving={isWorking}
          key={editingEntry.id}
          onCancel={() => setEditingEntry(null)}
          onSave={async (entryId, values) => {
            try {
              setIsWorking(true);
              await onUpdateEntry(entryId, values);
            } finally {
              setIsWorking(false);
            }
          }}
        />
      ) : null}
      <section
        aria-labelledby="payroll-entry-list-title"
        className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm"
      >
        <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
          <div>
            <h3
              className="text-base font-bold text-neutral-950"
              id="payroll-entry-list-title"
            >
              Chi tiết nhân viên
            </h3>
            <p className="mt-1 text-sm text-neutral-600">
              Kết quả được làm tròn đến 1 VND.
            </p>
          </div>
          <ReceiptText aria-hidden="true" className="size-5 text-neutral-400" />
        </div>
        {period.entries.length === 0 ? (
          <EmptyEntries />
        ) : (
          <>
            <div className="grid gap-3 p-4 sm:hidden">
              {period.entries.map((entry) => (
                <PayrollEntryCard
                  editable={editable}
                  entry={entry}
                  key={entry.id}
                  onEdit={setEditingEntry}
                />
              ))}
            </div>
            <PayrollEntryTable
              editable={editable}
              entries={period.entries}
              onEdit={setEditingEntry}
            />
          </>
        )}
      </section>
    </section>
  );
}
