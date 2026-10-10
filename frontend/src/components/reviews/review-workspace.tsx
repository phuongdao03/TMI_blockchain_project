"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Clock3,
  CheckCircle2,
  ClipboardCheck,
  Files,
  LoaderCircle,
  LockKeyhole,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EvidenceViewer } from "@/components/reviews/evidence-viewer";
import { FiveTScorecard } from "@/components/reviews/five-t-scorecard";
import { ReviewAssistancePanel } from "@/components/reviews/review-assistance-panel";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WorkflowNextStep } from "@/components/ui/workflow-next-step";
import { reviewApi } from "@/lib/api/client";
import type { ReviewAssignmentDetail, ReviewDraft } from "@/lib/api/types";
import { reviewKeys } from "@/lib/reviews/query-keys";

const statusLabels = {
  ASSIGNED: "Mới được giao",
  IN_PROGRESS: "Đang thẩm định",
  CONFLICTED: "Đã kết thúc",
  SUBMITTED: "Đã gửi kết quả",
  CANCELLED: "Đã hủy",
} as const;

export function reviewDeadlineState(dueAt: string | null, now = new Date()) {
  if (!dueAt) {
    return {
      status: "UNSCHEDULED" as const,
      label: "Chưa đặt thời hạn",
      detail: "Theo dõi thông báo từ quản lý thẩm định",
    };
  }
  const due = new Date(dueAt);
  const differenceHours = Math.ceil(
    (due.getTime() - now.getTime()) / 3_600_000,
  );
  const dateLabel = new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(due);
  if (differenceHours < 0) {
    return {
      status: "OVERDUE" as const,
      label: "Đã quá hạn xử lý",
      detail: `${dateLabel} · quá hạn ${Math.abs(differenceHours)} giờ`,
    };
  }
  return {
    status: "ON_TRACK" as const,
    label: differenceHours <= 24 ? "Sắp đến hạn" : "Còn trong thời hạn",
    detail: `${dateLabel} · còn ${differenceHours} giờ`,
  };
}

export function ReviewWorkspace({ assignmentId }: { assignmentId: string }) {
  const queryClient = useQueryClient();
  const [showConflictReason, setShowConflictReason] = useState(false);
  const [conflictReason, setConflictReason] = useState("");
  const query = useQuery({
    queryKey: reviewKeys.detail(assignmentId),
    queryFn: () => reviewApi.get(assignmentId),
  });
  const save = useMutation({
    mutationFn: (draft: ReviewDraft) =>
      reviewApi.saveDraft(assignmentId, draft),
  });
  const declareConflict = useMutation({
    mutationFn: (input: { hasConflict: boolean; reason?: string }) =>
      reviewApi.declareConflict(assignmentId, input),
    onSuccess: async (assignment) => {
      queryClient.setQueryData<ReviewAssignmentDetail>(
        reviewKeys.detail(assignmentId),
        (current) => (current ? { ...current, assignment } : current),
      );
      await queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(assignmentId),
      });
    },
  });
  const submit = useMutation({
    mutationFn: () => reviewApi.submit(assignmentId),
    onSuccess: (review) => {
      queryClient.setQueryData<ReviewAssignmentDetail>(
        reviewKeys.detail(assignmentId),
        (current) =>
          current
            ? {
                ...current,
                assignment: {
                  ...current.assignment,
                  status: "SUBMITTED",
                },
                review,
              }
            : current,
      );
    },
  });

  if (query.isPending) {
    return (
      <div className="grid min-h-[60vh] place-items-center" role="status">
        <span className="flex items-center gap-3 font-semibold text-neutral-600">
          <LoaderCircle className="size-5 animate-spin" />
          Đang mở hồ sơ thẩm định…
        </span>
      </div>
    );
  }
  if (query.error || !query.data) {
    return (
      <div
        className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-800"
        role="alert"
      >
        Không thể mở hồ sơ thẩm định hoặc bạn không còn quyền truy cập.
      </div>
    );
  }

  const detail = query.data;
  const deadline = reviewDeadlineState(detail.assignment.dueAt);
  const evidenceCount = detail.snapshotJson?.evidences.length ?? 0;
  const usesVerdictReview =
    detail.snapshotJson?.dossier.dossierType?.reviewRubric?.assessmentMethod ===
    "VERDICT";
  const terminal = ["CONFLICTED", "CANCELLED"].includes(
    detail.assignment.status,
  );
  return (
    <div className="review-workspace mx-auto max-w-[92rem] space-y-6">
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-[var(--theme-muted)] hover:text-[var(--theme-accent)]"
        href="/reviews"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Trở lại hàng đợi
      </Link>
      <header className="border-l-4 border-l-primary-700 border-y border-r border-[var(--theme-border)] bg-[var(--theme-surface)] px-6 py-6 text-[var(--theme-text)] sm:px-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--theme-accent)]">
              <ClipboardCheck className="size-4" />
              {detail.dossierCode} · Phiên bản {detail.versionNo}
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
              {detail.dossierTitle}
            </h1>
          </div>
          <span className="w-fit rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-1.5 text-xs font-bold text-[var(--theme-accent)]">
            {statusLabels[detail.assignment.status]}
          </span>
        </div>
      </header>

      {detail.assignment.status === "SUBMITTED" ? (
        <WorkflowNextStep
          action={{ href: "/reviews", label: "Về hàng đợi" }}
          description="Admin sẽ đọc báo cáo và ra quyết định cuối. Bạn có thể tiếp tục các hồ sơ khác trong hàng đợi."
          title="Đã gửi báo cáo cho Admin"
          tone="success"
        />
      ) : detail.assignment.status === "IN_PROGRESS" ? (
        <WorkflowNextStep
          action={{ href: "#review-form", label: "Tiếp tục báo cáo" }}
          description="Kiểm tra từng bằng chứng, lưu nội dung đang làm và gửi báo cáo khi đã hoàn tất. Sau khi gửi, Admin sẽ ra quyết định cuối."
          title="Việc cần làm · Hoàn tất báo cáo thẩm định"
        />
      ) : detail.assignment.status === "ASSIGNED" ? (
        <div className="space-y-4">
          <WorkflowNextStep
            description="Xác nhận có hay không có xung đột lợi ích trước khi xem tài liệu và lập báo cáo. Nếu có xung đột, phân công sẽ kết thúc để Admin giao người khác."
            title="Trước khi thẩm định · Xác nhận xung đột lợi ích"
          />
          <div className="space-y-4 border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                disabled={declareConflict.isPending}
                onClick={() => declareConflict.mutate({ hasConflict: false })}
              >
                {declareConflict.isPending ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="size-4 animate-spin"
                  />
                ) : null}
                Không có xung đột lợi ích
              </Button>
              <Button
                disabled={declareConflict.isPending}
                onClick={() => setShowConflictReason(true)}
                variant="outline"
              >
                Có xung đột lợi ích
              </Button>
            </div>
            {showConflictReason ? (
              <div className="space-y-3">
                <label
                  className="block text-sm font-semibold"
                  htmlFor="review-conflict-reason"
                >
                  Lý do xung đột
                </label>
                <textarea
                  className="min-h-24 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-3 text-sm"
                  id="review-conflict-reason"
                  maxLength={2000}
                  onChange={(event) => setConflictReason(event.target.value)}
                  value={conflictReason}
                />
                <Button
                  disabled={declareConflict.isPending || !conflictReason.trim()}
                  onClick={() =>
                    declareConflict.mutate({
                      hasConflict: true,
                      reason: conflictReason.trim(),
                    })
                  }
                >
                  Xác nhận xung đột
                </Button>
              </div>
            ) : null}
            {declareConflict.error ? (
              <p className="text-sm font-semibold text-error" role="alert">
                Không thể xác nhận phân công. {declareConflict.error.message}
              </p>
            ) : null}
          </div>
        </div>
      ) : detail.assignment.status === "CONFLICTED" ? (
        <WorkflowNextStep
          action={{ href: "/reviews", label: "Về hàng đợi" }}
          description="Đã ghi nhận xung đột lợi ích và kết thúc phân công này. Admin sẽ chọn người thẩm định khác; bạn có thể tiếp tục công việc còn lại."
          title="Đã báo xung đột cho Admin"
          tone="success"
        />
      ) : null}

      {["IN_PROGRESS", "SUBMITTED"].includes(detail.assignment.status) &&
      detail.snapshotJson ? (
        <nav
          aria-label="Đi tới nội dung thẩm định"
          className="flex flex-wrap gap-2"
        >
          <a
            className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href="#review-evidence"
          >
            <Files
              aria-hidden="true"
              className="size-4 text-[var(--theme-accent)]"
            />
            Xem tài liệu
          </a>
          <a
            className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href="#review-scorecard"
          >
            <ClipboardCheck
              aria-hidden="true"
              className="size-4 text-[var(--theme-accent)]"
            />
            Mở phiếu thẩm định
          </a>
        </nav>
      ) : null}

      <ol
        aria-label="Quy trình thẩm định"
        className="grid gap-3 border-b border-[var(--theme-border)] pb-6 md:grid-cols-3"
      >
        {(usesVerdictReview
          ? [
              ["01", "Kiểm tra bằng chứng", "Xem từng tài liệu đã khóa"],
              ["02", "Lập báo cáo", "Kết luận và nêu căn cứ"],
              ["03", "Gửi Admin", "Xác nhận và hoàn tất"],
            ]
          : [
              ["01", "Kiểm tra bằng chứng", "Xem tài liệu đã khóa"],
              ["02", "Đánh giá 5T", "Chấm điểm và ghi nhận xét"],
              ["03", "Gửi Admin", "Xác nhận và hoàn tất"],
            ]
        ).map(([number, title, description]) => (
          <li className="grid grid-cols-[2rem_1fr] gap-3 py-2" key={number}>
            <span className="grid size-8 place-items-center rounded-full bg-[var(--theme-elevated)] font-mono text-xs font-bold text-[var(--theme-accent)]">
              {number}
            </span>
            <div>
              <p className="text-sm font-bold">{title}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
                {description}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <section
        aria-label="Thông tin kiểm soát phiên thẩm định"
        className="grid overflow-hidden border-y border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)] sm:grid-cols-3"
      >
        <article className="border-b border-[var(--theme-border)] p-4 sm:border-b-0 sm:border-r sm:p-5">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
            <Clock3 aria-hidden="true" className="size-4" /> Thời hạn xử lý
          </p>
          <p
            className={`mt-2 font-bold ${deadline.status === "OVERDUE" ? "text-error" : ""}`}
          >
            {deadline.label}
          </p>
          <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
            {deadline.detail}
          </p>
        </article>
        <article className="border-b border-[var(--theme-border)] p-4 sm:border-b-0 sm:border-r sm:p-5">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
            <Files aria-hidden="true" className="size-4" /> Bộ bằng chứng
          </p>
          <p className="mt-2 font-bold">{evidenceCount} tài liệu đã khóa</p>
          <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
            Chỉ dẫn chiếu nội dung thuộc phiên bản {detail.versionNo}
          </p>
        </article>
        <article className="p-4 sm:p-5">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
            <LockKeyhole aria-hidden="true" className="size-4" /> Phạm vi thao
            tác
          </p>
          <p className="mt-2 font-bold">Thẩm định nội bộ</p>
          <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
            Không thể sửa hồ sơ hoặc đưa ra quyết định cuối cùng
          </p>
        </article>
      </section>

      {save.error || submit.error ? (
        <p
          className="review-workspace__error rounded-xl border p-4 text-sm font-semibold"
          role="alert"
        >
          <span className="block font-bold">
            Không thể lưu hoặc gửi phiếu thẩm định.
          </span>
          <span className="mt-1 block font-medium">
            {(submit.error ?? save.error)?.message ||
              "Nội dung vẫn còn trên màn hình; vui lòng thử lại."}
          </span>
        </p>
      ) : null}
      <ReviewAssistancePanel
        assignmentId={assignmentId}
        canRequest={detail.assignment.status === "IN_PROGRESS"}
        requests={detail.assistanceRequests ?? []}
      />
      {terminal ? (
        <Card className="p-8 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-50 text-amber-700">
            <AlertTriangle className="size-6" />
          </span>
          <h2 className="mt-4 text-xl font-bold">Phân công đã kết thúc</h2>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">
            Hồ sơ không còn khả dụng để tiếp tục thẩm định.
          </p>
        </Card>
      ) : null}
      {["IN_PROGRESS", "SUBMITTED"].includes(detail.assignment.status) &&
      detail.snapshotJson ? (
        <div
          className="grid items-start gap-6 xl:grid-cols-[minmax(21rem,0.85fr)_minmax(34rem,1.15fr)]"
          id="review-form"
        >
          <aside
            aria-label="Hồ sơ và tài liệu kiểm chứng"
            className="min-w-0 scroll-mt-24 space-y-4"
            id="review-evidence"
          >
            {detail.snapshotJson.dossier.summary ? (
              <Card className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
                  Tóm tắt của người nộp
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--theme-text)]">
                  {detail.snapshotJson.dossier.summary}
                </p>
              </Card>
            ) : null}
            <EvidenceViewer
              documentRules={
                detail.snapshotJson.dossier.dossierType?.documentRules
              }
              evidences={detail.snapshotJson.evidences ?? []}
            />
            <details className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm">
              <summary className="flex cursor-pointer items-center gap-2 font-semibold text-[var(--theme-text)]">
                <CheckCircle2
                  aria-hidden="true"
                  className="size-4 text-emerald-700"
                />
                Dấu vân tay phiên bản
              </summary>
              <code className="mt-3 block break-all text-xs leading-5 text-[var(--theme-muted)]">
                {detail.canonicalHash}
              </code>
            </details>
          </aside>
          <div className="min-w-0 scroll-mt-24" id="review-scorecard">
            <FiveTScorecard
              evidences={detail.snapshotJson.evidences ?? []}
              initialReview={detail.review}
              isSaving={save.isPending}
              isSubmitting={submit.isPending}
              onSave={async (draft) => {
                await save.mutateAsync(draft);
              }}
              onSubmit={async () => {
                await submit.mutateAsync();
              }}
              readOnly={detail.assignment.status === "SUBMITTED"}
              requireEvidenceAssessments={
                detail.snapshotJson.schemaVersion >= 2
              }
              rubric={detail.snapshotJson.dossier.dossierType?.reviewRubric}
              saveError={save.error}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
