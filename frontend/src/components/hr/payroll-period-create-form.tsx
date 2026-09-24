"use client";

import { CalendarPlus, Plus } from "lucide-react";
import { type FormEvent, useState } from "react";

import type { AttendanceWorksite } from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-neutral-100";

function currentMonthInput() {
  const current = new Date();
  return `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}`;
}

export function PayrollPeriodCreateForm({
  worksites,
  isSubmitting,
  errorMessage,
  onSubmit,
}: {
  worksites: AttendanceWorksite[];
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (input: {
    worksiteId: string;
    periodMonth: string;
    standardWorkdays: number;
  }) => Promise<void>;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [worksiteId, setWorksiteId] = useState("");
  const [month, setMonth] = useState(currentMonthInput);
  const [standardWorkdays, setStandardWorkdays] = useState("22");
  const activeWorksites = worksites.filter((item) => item.status === "ACTIVE");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await onSubmit({
        worksiteId,
        periodMonth: `${month}-01`,
        standardWorkdays: Number(standardWorkdays),
      });
      setIsOpen(false);
    } catch {
      // The parent renders the API error next to the form.
    }
  }

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-950">Kỳ lương mới</h2>
          <p className="mt-1 text-sm leading-5 text-neutral-600">
            Tạo bản nháp theo địa điểm và tháng. Số liệu chỉ được khóa sau khi
            xác nhận.
          </p>
        </div>
        <button
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-neutral-950 px-4 text-sm font-bold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={activeWorksites.length === 0}
          onClick={() => setIsOpen((current) => !current)}
          type="button"
        >
          <Plus aria-hidden="true" className="size-4" />
          {isOpen ? "Đóng biểu mẫu" : "Tạo kỳ lương"}
        </button>
      </div>
      {activeWorksites.length === 0 ? (
        <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
          Cần có ít nhất một địa điểm làm việc đang hoạt động trước khi tạo kỳ
          lương.
        </p>
      ) : null}
      {isOpen ? (
        <form
          className="mt-5 grid gap-4 border-t border-neutral-200 pt-5 md:grid-cols-3"
          onSubmit={submit}
        >
          <label className="text-sm font-bold text-neutral-800">
            Địa điểm làm việc
            <select
              className={fieldClass}
              onChange={(event) => setWorksiteId(event.target.value)}
              required
              value={worksiteId}
            >
              <option value="">Chọn địa điểm</option>
              {activeWorksites.map((worksite) => (
                <option key={worksite.id} value={worksite.id}>
                  {worksite.name} ({worksite.code})
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Tháng áp dụng
            <span className="relative mt-2 block">
              <CalendarPlus
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-3.5 size-4 text-neutral-400"
              />
              <input
                className={`${fieldClass} mt-0 pl-10`}
                onChange={(event) => setMonth(event.target.value)}
                required
                type="month"
                value={month}
              />
            </span>
          </label>
          <label className="text-sm font-bold text-neutral-800">
            Ngày công chuẩn
            <input
              className={fieldClass}
              max="31"
              min="1"
              onChange={(event) => setStandardWorkdays(event.target.value)}
              required
              step="1"
              type="number"
              value={standardWorkdays}
            />
          </label>
          {errorMessage ? (
            <p
              className="text-sm font-semibold text-red-700 md:col-span-2"
              role="alert"
            >
              {errorMessage}
            </p>
          ) : null}
          <div className="flex justify-end md:col-start-3">
            <button
              className="min-h-11 w-full rounded-xl bg-primary-700 px-5 text-sm font-bold text-white transition hover:bg-primary-800 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Đang tạo..." : "Tạo bản nháp"}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
