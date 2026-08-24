import { CheckCircle2, CircleAlert, Clock3 } from "lucide-react";

import type { DossierStatus, DossierTimelineItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const workflowStages: Array<{
  statuses: readonly DossierStatus[];
  label: string;
}> = [
  { statuses: ["DRAFT"], label: "Chuẩn bị hồ sơ" },
  {
    statuses: ["SUBMITTED", "PRECHECK", "NEEDS_SUPPLEMENT"],
    label: "Kiểm tra ban đầu",
  },
  { statuses: ["UNDER_REVIEW", "COUNCIL_REVIEW"], label: "Thẩm định" },
  { statuses: ["APPROVED", "PAYMENT_PENDING"], label: "Hoàn tất lệ phí" },
  {
    statuses: ["PAID", "ANCHOR_PENDING", "ANCHORED"],
    label: "Chuẩn bị chứng thư",
  },
  { statuses: ["CERTIFICATE_ISSUED", "PUBLISHED"], label: "Nhận chứng thư" },
];

const exceptionStatuses = new Set<DossierStatus>([
  "NEEDS_SUPPLEMENT",
  "REJECTED",
  "CANCELLED",
  "REVOKED",
]);

export function DossierWorkflowTimeline({
  status,
  history,
}: {
  status: DossierStatus;
  history: readonly DossierTimelineItem[];
}) {
  const currentIndex = workflowStages.findIndex((stage) =>
    stage.statuses.includes(status),
  );
  const completedStatuses = new Set(history.map((item) => item.toStatus));
  const exception = exceptionStatuses.has(status);

  return (
    <section
      aria-labelledby="dossier-workflow-heading"
      className="dossier-workflow py-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 px-1">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Tiến độ hồ sơ
          </p>
          <h2
            className="mt-1 text-xl font-bold tracking-tight text-neutral-950"
            id="dossier-workflow-heading"
          >
            Từ chuẩn bị đến nhận chứng thư
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-neutral-500">
            Theo dõi chặng đang xử lý và phần việc sắp tới của hồ sơ.
          </p>
        </div>
        {exception ? (
          <span className="dossier-workflow__exception inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold">
            <CircleAlert aria-hidden="true" className="size-4" />
            {status === "NEEDS_SUPPLEMENT"
              ? "Cần bạn bổ sung"
              : status === "REJECTED"
                ? "Chưa đủ điều kiện"
                : status === "REVOKED"
                  ? "Chứng thư đã thu hồi"
                  : "Hồ sơ đã hủy"}
          </span>
        ) : null}
      </div>

      <ol className="dossier-workflow__track mt-6 grid gap-px overflow-hidden sm:grid-cols-2 lg:grid-cols-6">
        {workflowStages.map((stage, index) => {
          const isCurrent = stage.statuses.includes(status);
          const isComplete =
            stage.statuses.some((stageStatus) =>
              completedStatuses.has(stageStatus),
            ) ||
            (currentIndex > index && currentIndex >= 0);
          return (
            <li
              className={cn(
                "dossier-workflow__stage min-h-28 p-4",
                isCurrent && "dossier-workflow__stage--current",
              )}
              key={stage.label}
            >
              <span
                className={cn(
                  "grid size-8 place-items-center rounded-full",
                  isCurrent
                    ? "bg-primary-700 text-white"
                    : isComplete
                      ? "bg-emerald-600 text-white"
                      : "bg-neutral-100 text-neutral-500",
                )}
              >
                {isComplete ? (
                  <CheckCircle2 aria-hidden="true" className="size-4" />
                ) : (
                  <Clock3 aria-hidden="true" className="size-4" />
                )}
              </span>
              <p className="mt-3 text-sm font-bold text-neutral-900">
                {stage.label}
              </p>
              <p className="mt-1 text-xs text-neutral-500">
                {isCurrent
                  ? "Đang thực hiện"
                  : isComplete
                    ? "Đã hoàn tất"
                    : "Sắp tới"}
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
