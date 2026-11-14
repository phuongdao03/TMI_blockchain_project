import { CheckCircle2, CircleAlert, Clock3 } from "lucide-react";
import {
  dossierProgress,
  type ProgressInput,
} from "@/components/dossiers/dossier-progress";

export function DossierWorkflowTimeline({
  audience = "applicant",
  ...input
}: ProgressInput & { audience?: "applicant" | "staff" }) {
  const progress = dossierProgress(input);
  return (
    <section
      aria-label="Tiến độ hồ sơ"
      className="border-y border-[var(--theme-border)] py-5 text-[var(--theme-text)]"
    >
      <p className="text-xs font-bold uppercase tracking-wider text-[var(--theme-accent)]">
        Tiến độ hồ sơ
      </p>
      <h2 className="mt-2 text-lg font-bold">
        {input.status === "NEEDS_SUPPLEMENT" && audience === "staff"
          ? "Đang chờ người nộp bổ sung"
          : progress.current}
      </h2>
      {progress.next ? (
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Bước tiếp theo:{" "}
          {input.status === "NEEDS_SUPPLEMENT"
            ? audience === "staff"
              ? "Tiếp tục xử lý khi phản hồi bổ sung được chấp nhận"
              : "Phản hồi yêu cầu bổ sung"
            : progress.next}
        </p>
      ) : null}
      {input.status === "REJECTED" ? (
        <p className="mt-1 text-sm">Chưa đủ điều kiện</p>
      ) : null}
      <details className="mt-3">
        <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold text-[var(--theme-accent)]">
          Xem toàn bộ tiến độ
        </summary>
        <p className="text-sm text-[var(--theme-muted)]">
          Từ chuẩn bị đến công bố
        </p>
        <ol className="mt-3 space-y-0">
          {progress.stages.map((stage) => (
            <li
              key={stage.key}
              aria-current={
                stage.state === "current" || stage.state === "supplement"
                  ? "step"
                  : undefined
              }
              className="flex min-w-0 gap-3 border-l border-[var(--theme-border)] pb-5 pl-4"
            >
              {stage.state === "complete" ? (
                <CheckCircle2
                  aria-hidden
                  className="mt-1 size-4 shrink-0 text-emerald-600"
                />
              ) : stage.state === "stopped" || stage.state === "supplement" ? (
                <CircleAlert
                  aria-hidden
                  className="mt-1 size-4 shrink-0 text-[var(--theme-accent)]"
                />
              ) : (
                <Clock3 aria-hidden className="mt-1 size-4 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-semibold">{stage.label}</p>
                <p className="text-xs text-[var(--theme-muted)]">
                  {stage.state === "complete"
                    ? "Đã hoàn tất"
                    : stage.state === "current"
                      ? "Đang thực hiện"
                      : stage.state === "supplement"
                        ? "Cần bổ sung"
                        : stage.state === "stopped"
                          ? "Đã dừng"
                          : "Chưa bắt đầu"}
                </p>
                {stage.detail ? (
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                    {stage.detail}
                  </p>
                ) : null}
                {stage.completedAt ? (
                  <time
                    className="text-xs text-[var(--theme-muted)]"
                    dateTime={stage.completedAt}
                  >
                    {new Date(stage.completedAt).toLocaleString("vi-VN")}
                  </time>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
