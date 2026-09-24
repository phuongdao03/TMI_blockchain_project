"use client";

import { CalendarDays, FileText, RefreshCw } from "lucide-react";

import {
  formatPayrollMonth,
  payrollStatusLabels,
  payrollStatusTones,
} from "@/components/hr/payroll-format";
import type { AttendanceWorksite, PayrollPeriod } from "@/lib/api/types";

export function PayrollPeriodList({
  periods,
  worksites,
  selectedId,
  isLoading,
  errorMessage,
  onSelect,
  onRetry,
}: {
  periods: PayrollPeriod[];
  worksites: AttendanceWorksite[];
  selectedId: string | null;
  isLoading: boolean;
  errorMessage: string | null;
  onSelect: (periodId: string) => void;
  onRetry: () => void;
}) {
  const worksiteNameById = new Map(
    worksites.map((item) => [item.id, item.name]),
  );

  if (isLoading) {
    return (
      <div
        className="h-48 animate-pulse rounded-2xl bg-neutral-100"
        aria-label="Đang tải kỳ lương"
      />
    );
  }
  if (errorMessage) {
    return (
      <section
        className="rounded-2xl border border-red-200 bg-red-50 p-5"
        role="alert"
      >
        <h2 className="font-bold text-red-950">
          Không tải được danh sách kỳ lương
        </h2>
        <p className="mt-1 text-sm text-red-800">{errorMessage}</p>
        <button
          className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg bg-white px-3 text-sm font-bold text-red-900 shadow-sm"
          onClick={onRetry}
          type="button"
        >
          <RefreshCw aria-hidden="true" className="size-4" /> Thử lại
        </button>
      </section>
    );
  }
  if (periods.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-neutral-300 bg-white p-8 text-center">
        <FileText
          aria-hidden="true"
          className="mx-auto size-9 text-neutral-400"
        />
        <h2 className="mt-3 font-bold text-neutral-950">Chưa có kỳ lương</h2>
        <p className="mx-auto mt-1 max-w-md text-sm leading-5 text-neutral-600">
          Tạo kỳ lương theo địa điểm làm việc để tập hợp ngày công và tăng ca đã
          được duyệt.
        </p>
      </section>
    );
  }
  return (
    <section
      aria-labelledby="payroll-period-list-title"
      className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm"
    >
      <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
        <div>
          <h2
            className="text-base font-bold text-neutral-950"
            id="payroll-period-list-title"
          >
            Kỳ lương
          </h2>
          <p className="mt-1 text-sm text-neutral-600">
            Chọn một kỳ để kiểm tra và xử lý số liệu.
          </p>
        </div>
        <span className="text-sm font-semibold text-neutral-500">
          {periods.length} kỳ
        </span>
      </div>
      <div className="divide-y divide-neutral-100 sm:hidden">
        {periods.map((period) => {
          const selected = period.id === selectedId;
          return (
            <button
              className={`w-full px-5 py-4 text-left ${selected ? "bg-primary-50" : "bg-white"}`}
              key={period.id}
              onClick={() => onSelect(period.id)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold text-neutral-950">
                    {formatPayrollMonth(period.periodMonth)}
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    {worksiteNameById.get(period.worksiteId) ??
                      "Địa điểm đã lưu"}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${payrollStatusTones[period.status]}`}
                >
                  {payrollStatusLabels[period.status]}
                </span>
              </div>
              <p className="mt-3 text-sm text-neutral-600">
                {period.standardWorkdays} ngày công chuẩn
              </p>
            </button>
          );
        })}
      </div>
      <div className="hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[700px] text-left">
          <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-5 py-3">Kỳ</th>
              <th className="px-5 py-3">Địa điểm</th>
              <th className="px-5 py-3">Ngày chuẩn</th>
              <th className="px-5 py-3">Trạng thái</th>
              <th className="px-5 py-3">
                <span className="sr-only">Mở chi tiết</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {periods.map((period) => {
              const selected = period.id === selectedId;
              return (
                <tr
                  className={`border-t border-neutral-100 ${selected ? "bg-primary-50/70" : "hover:bg-neutral-50"}`}
                  key={period.id}
                >
                  <td className="px-5 py-4 font-bold text-neutral-950">
                    {formatPayrollMonth(period.periodMonth)}
                  </td>
                  <td className="px-5 py-4 text-sm text-neutral-700">
                    {worksiteNameById.get(period.worksiteId) ??
                      "Địa điểm đã lưu"}
                  </td>
                  <td className="px-5 py-4 text-sm text-neutral-700">
                    {period.standardWorkdays}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-bold ${payrollStatusTones[period.status]}`}
                    >
                      {payrollStatusLabels[period.status]}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <button
                      className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 hover:bg-white"
                      onClick={() => onSelect(period.id)}
                      type="button"
                    >
                      <CalendarDays aria-hidden="true" className="size-4" />
                      {selected ? "Đang xem" : "Xem kỳ"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
