import { ClipboardCheck } from "lucide-react";

import { ReviewAssignmentList } from "@/components/reviews/review-assignment-list";
import type { ReviewAssignmentStatus } from "@/lib/api/types";

const statuses: Array<[string, string]> = [
  ["", "Tất cả phân công"],
  ["ASSIGNED", "Chờ xác nhận"],
  ["IN_PROGRESS", "Đang thẩm định"],
  ["SUBMITTED", "Đã gửi kết quả"],
  ["CONFLICTED", "Đã báo xung đột"],
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
    <div className="review-queue mx-auto max-w-7xl space-y-7">
      <header className="review-queue__intro">
        <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          <ClipboardCheck aria-hidden="true" className="size-4" />
          Không gian chuyên gia
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
          Hàng đợi thẩm định
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
          Kiểm tra xung đột lợi ích, đánh giá bằng chứng và hoàn tất phiếu điểm
          5T theo từng phiên bản hồ sơ.
        </p>
      </header>
      <ol
        aria-label="Quy trình thẩm định"
        className="review-queue__steps grid gap-px overflow-hidden rounded-2xl border bg-neutral-200 sm:grid-cols-3"
      >
        {[
          ["01", "Xác nhận độc lập", "Khai báo xung đột lợi ích trước khi xem hồ sơ."],
          ["02", "Đánh giá bằng chứng", "Kiểm tra tài liệu và hoàn thiện rubric đúng loại hồ sơ."],
          ["03", "Gửi kết quả", "Kiểm tra toàn bộ phiếu trước khi khóa và gửi."],
        ].map(([step, title, description]) => (
          <li className="review-queue__step bg-white p-5" key={step}>
            <p className="font-mono text-xs font-bold text-primary-700">{step}</p>
            <h2 className="mt-2 font-bold text-neutral-950">{title}</h2>
            <p className="mt-1 text-sm leading-6 text-neutral-600">{description}</p>
          </li>
        ))}
      </ol>
      <form className="review-queue__filters flex flex-col gap-3 rounded-2xl border bg-white p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label
            className="text-xs font-bold uppercase tracking-wider text-neutral-500"
            htmlFor="review-status"
          >
            Trạng thái phân công
          </label>
          <select
            className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3 text-sm font-semibold sm:max-w-xs"
            defaultValue={status ?? ""}
            id="review-status"
            name="status"
          >
            {statuses.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button
          className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng bộ lọc
        </button>
      </form>
      <ReviewAssignmentList page={page} pageSize={10} status={status} />
    </div>
  );
}
