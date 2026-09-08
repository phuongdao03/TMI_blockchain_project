import { ClipboardCheck } from "lucide-react";

import { ReviewAssignmentList } from "@/components/reviews/review-assignment-list";
import { SelectControl } from "@/components/ui/form-controls";
import type { ReviewAssignmentStatus } from "@/lib/api/types";

const statuses: Array<[string, string]> = [
  ["", "Tất cả phân công"],
  ["IN_PROGRESS", "Đang thẩm định"],
  ["SUBMITTED", "Đã gửi kết quả"],
];

export default async function ReviewQueuePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; status?: string }>;
}) {
  const parameters = await searchParams;
  const page = Math.max(1, Number(parameters.page) || 1);
  const status = statuses.some(([value]) => value === parameters.status)
    ? (parameters.status as ReviewAssignmentStatus | undefined)
    : undefined;

  return (
    <div className="review-queue mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="review-queue__intro border-b border-neutral-200 pb-7">
        <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          <ClipboardCheck aria-hidden="true" className="size-4" />
          Trung tâm kiểm duyệt
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
          Công việc kiểm duyệt
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
          Làm việc trên các hồ sơ được Admin phân công, đối chiếu bằng chứng và
          gửi báo cáo độc lập để Admin ra quyết định cuối.
        </p>
      </header>
      <form className="review-queue__filters grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:grid-cols-[minmax(0,20rem)_auto] sm:items-end sm:justify-start">
        <div>
          <label
            className="text-xs font-bold uppercase tracking-wider text-neutral-500"
            htmlFor="review-status"
          >
            Trạng thái phân công
          </label>
          <SelectControl
            className="mt-2 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 text-sm font-semibold"
            defaultValue={status ?? ""}
            id="review-status"
            name="status"
          >
            {statuses.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectControl>
        </div>
        <button
          className="min-h-11 rounded-lg bg-neutral-950 px-5 text-sm font-bold text-white hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng bộ lọc
        </button>
      </form>
      <ReviewAssignmentList page={page} pageSize={10} status={status} />
    </div>
  );
}
