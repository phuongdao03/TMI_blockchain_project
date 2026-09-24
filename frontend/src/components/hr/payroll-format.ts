import type { PayrollPeriodStatus } from "@/lib/api/types";

export const payrollStatusLabels: Record<PayrollPeriodStatus, string> = {
  DRAFT: "Bản nháp",
  CONFIRMED: "Đã xác nhận",
  PAID: "Đã chi",
};

export const payrollStatusTones: Record<PayrollPeriodStatus, string> = {
  DRAFT: "bg-amber-50 text-amber-900 ring-1 ring-amber-200",
  CONFIRMED: "bg-sky-50 text-sky-900 ring-1 ring-sky-200",
  PAID: "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200",
};

export function formatVnd(value: string) {
  const match = /^(-?)(\d+)(?:\.\d+)?$/.exec(value.trim());
  if (!match) return "Không hợp lệ";
  const sign = match[1] ?? "";
  const integer = match[2];
  if (!integer) return "Không hợp lệ";
  const normalized = integer.replace(/^0+(?=\d)/, "");
  return `${sign}${normalized.replace(/\B(?=(\d{3})+(?!\d))/g, ".")} ₫`;
}

export function formatPayrollMonth(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

export function formatTimestamp(value: string | null) {
  if (!value) return "Chưa tính";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function payrollApiMessage(error: unknown) {
  if (error instanceof Error && error.message) return error.message;
  return "Không thể cập nhật bảng lương. Vui lòng thử lại.";
}
