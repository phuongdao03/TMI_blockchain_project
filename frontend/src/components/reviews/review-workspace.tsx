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
  const terminal = ["CONFLICTED", "CANCELLED"].includes(
    detail.assignment.status,
  );
  return (
    <div className="review-workspace mx-auto max-w-[92rem] space-y-4 sm:space-y-6">
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-[var(--theme-muted)] hover:text-[var(--theme-accent)]"
        href="/reviews"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Trở lại hàng đợi
      </Link>
      <header className="border-b border-[var(--theme-border)] pb-4 text-[var(--theme-text)]">
        <div className="flex flex-col justify-between gap-2 lg:flex-row lg:items-center">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--theme-accent)]">
              <ClipboardCheck className="size-4" />
              {detail.dossierCode} · Phiên bản {detail.versionNo}
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
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
          description="Bạn có thể tiếp tục công việc khác trong hàng đợi."
          title="Đã gửi báo cáo thẩm định"
          tone="success"
          variant="inline"
        />
      ) : detail.assignment.status === "IN_PROGRESS" ? (
        <p className="text-sm text-[var(--theme-muted)]">
          Đối chiếu tài liệu và hoàn thành phiếu thẩm định.
        </p>
      ) : detail.assignment.status === "ASSIGNED" ? (
        <div className="space-y-4">
          <WorkflowNextStep
            description="Xác nhận trước khi mở tài liệu và lập báo cáo."
            title="Xung đột lợi ích"
            variant="inline"
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
          description="Phân công này đã kết thúc."
          title="Đã ghi nhận xung đột lợi ích"
          tone="success"
          variant="inline"
        />
      ) : null}

      {["IN_PROGRESS", "SUBMITTED"].includes(detail.assignment.status) &&
      detail.snapshotJson ? (
        <nav
          aria-label="Đi tới nội dung thẩm định"
          className="flex flex-wrap gap-x-5 gap-y-1 border-b border-[var(--theme-border)] pb-2"
        >
          <a
            className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href="#review-evidence"
          >
            <Files
              aria-hidden="true"
              className="size-4 text-[var(--theme-accent)]"
            />
            Xem tài liệu
          </a>
          <a
            className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href="#review-scorecard"
          >
            <ClipboardCheck
              aria-hidden="true"
              className="size-4 text-[var(--theme-accent)]"
            />
            Mở phiếu thẩm định
          </a>
          {detail.assignment.status === "IN_PROGRESS" ? (
            <a
              className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href="#review-assistance"
            >
              Yêu cầu hỗ trợ
            </a>
          ) : null}
        </nav>
      ) : null}

      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--theme-muted)]">
        <span>
          <Clock3 aria-hidden="true" className="mr-1 inline size-3.5" />
          {deadline.label} · {deadline.detail}
        </span>
        <span>
          <Files aria-hidden="true" className="mr-1 inline size-3.5" />
          {evidenceCount} tài liệu
        </span>
      </div>

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
        <div className="space-y-8" id="review-form">
          <aside
            aria-label="Hồ sơ và tài liệu kiểm chứng"
            className="min-w-0 scroll-mt-24 space-y-4"
            id="review-evidence"
          >
            {detail.snapshotJson.dossier.summary ? (
              <div className="pb-2">
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--theme-muted)]">
                  Tóm tắt của người nộp
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--theme-text)]">
                  {detail.snapshotJson.dossier.summary}
                </p>
              </div>
            ) : null}
            <EvidenceViewer
              documentRules={
                detail.snapshotJson.dossier.dossierType?.documentRules
              }
              evidences={detail.snapshotJson.evidences ?? []}
            />
            <details className="py-3 text-sm">
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
      <ReviewAssistancePanel
        assignmentId={assignmentId}
        canRequest={detail.assignment.status === "IN_PROGRESS"}
        requests={detail.assistanceRequests ?? []}
      />
    </div>
  );
}
