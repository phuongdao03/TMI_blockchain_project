import { ChevronDown, ClipboardList, Inbox, LoaderCircle } from "lucide-react";

import type { WorkAllocation, WorkAllocationDetail } from "@/lib/api/types";

const statusLabels = {
  DRAFT: "Bản nháp",
  ACTIVE: "Đang thực hiện",
  COMPLETED: "Hoàn thành",
  CANCELLED: "Đã hủy",
} as const;

const priorityLabels = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Khẩn cấp",
} as const;

export function WorkAllocationList({
  rows,
  isPending,
  isError,
  selectedAllocationId,
  selectedDetail,
  isDetailPending,
  isDetailError,
  onSelect,
}: {
  rows: WorkAllocation[];
  isPending: boolean;
  isError: boolean;
  selectedAllocationId: string | null;
  selectedDetail: WorkAllocationDetail | null;
  isDetailPending: boolean;
  isDetailError: boolean;
  onSelect: (allocationId: string | null) => void;
}) {
  if (isPending) {
    return (
      <div
        aria-busy="true"
        className="grid min-h-56 place-items-center"
        role="status"
      >
        <LoaderCircle
          aria-hidden="true"
          className="size-6 animate-spin text-primary-700"
        />
        <span className="sr-only">Đang tải danh sách phân công</span>
      </div>
    );
  }
  if (isError) {
    return (
      <p
        className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm font-semibold text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        role="alert"
      >
        Chưa thể tải danh sách phân công. Vui lòng thử lại.
      </p>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-neutral-300 px-5 py-10 text-center dark:border-neutral-700">
        <Inbox aria-hidden="true" className="mx-auto size-9 text-neutral-400" />
        <h2 className="mt-4 text-xl font-bold text-neutral-950 dark:text-white">
          Chưa có phân công
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600 dark:text-neutral-300">
          Tạo công việc chung hoặc chuẩn bị hồ sơ cần thẩm định để bắt đầu phân
          chia trách nhiệm.
        </p>
      </div>
    );
  }
  return (
    <div className="grid gap-3" role="list">
      {rows.map((allocation) => (
        <article
          className="rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900 sm:p-5"
          key={allocation.id}
          role="listitem"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
                <ClipboardList aria-hidden="true" className="size-5" />
              </span>
              <div className="min-w-0">
                <h2 className="truncate font-bold text-neutral-950 dark:text-white">
                  {allocation.objective}
                </h2>
                <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
                  {allocation.kind === "DOSSIER_REVIEW"
                    ? "Hồ sơ thẩm định"
                    : "Công việc chung"}
                </p>
              </div>
            </div>
            <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
              {statusLabels[allocation.status]}
            </span>
          </div>
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-300">
            Ưu tiên {priorityLabels[allocation.priority]}
            {allocation.dueAt
              ? ` · Hạn ${new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(allocation.dueAt))}`
              : " · Chưa đặt hạn"}
          </p>
          <button
            aria-expanded={selectedAllocationId === allocation.id}
            className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 transition hover:border-primary-400 hover:text-primary-700 dark:border-neutral-700 dark:text-neutral-100 dark:hover:border-primary-400 dark:hover:text-primary-200"
            onClick={() =>
              onSelect(
                selectedAllocationId === allocation.id ? null : allocation.id,
              )
            }
            type="button"
          >
            <ChevronDown
              aria-hidden="true"
              className={`size-4 transition ${
                selectedAllocationId === allocation.id ? "rotate-180" : ""
              }`}
            />
            {selectedAllocationId === allocation.id
              ? "Ẩn phạm vi"
              : "Xem phạm vi"}
          </button>
          {selectedAllocationId === allocation.id ? (
            <AllocationCoverage
              detail={selectedDetail}
              isError={isDetailError}
              isPending={isDetailPending}
            />
          ) : null}
        </article>
      ))}
    </div>
  );
}

function AllocationCoverage({
  detail,
  isPending,
  isError,
}: {
  detail: WorkAllocationDetail | null;
  isPending: boolean;
  isError: boolean;
}) {
  if (isPending) {
    return (
      <p
        className="mt-4 flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300"
        role="status"
      >
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        Đang tải phạm vi được giao...
      </p>
    );
  }
  if (isError || !detail) {
    return (
      <p
        className="mt-4 text-sm font-semibold text-red-700 dark:text-red-300"
        role="alert"
      >
        Chưa thể tải phạm vi và người phụ trách. Vui lòng thử lại.
      </p>
    );
  }
  if (detail.scopes.length === 0) {
    return (
      <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-300">
        Công việc chung này không giới hạn theo tài liệu hồ sơ.
      </p>
    );
  }
  const coverageByScope = new Map(
    detail.scopeCoverage.map((coverage) => [coverage.scopeId, coverage]),
  );
  return (
    <section className="mt-4 border-t border-neutral-200 pt-4 dark:border-neutral-800">
      <h3 className="text-sm font-bold text-neutral-950 dark:text-white">
        Phạm vi tài liệu
      </h3>
      <ul className="mt-3 space-y-2">
        {detail.scopes.map((scope) => {
          const reviewerCount =
            coverageByScope.get(scope.id)?.reviewerUserIds.length ?? 0;
          return (
            <li
              className="rounded-lg bg-neutral-50 px-3 py-2 text-sm dark:bg-neutral-950"
              key={scope.id}
            >
              <p className="font-semibold text-neutral-900 dark:text-neutral-100">
                {scope.dossierEvidenceTitle ??
                  scope.groupLabel ??
                  "Tài liệu đã chọn"}
              </p>
              <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-300">
                {scope.requiresDualReview ? "Thẩm định kép" : "Thẩm định đơn"} ·{" "}
                {reviewerCount} người phụ trách
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
