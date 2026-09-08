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

import { EvidenceViewer } from "@/components/reviews/evidence-viewer";
import { FiveTScorecard } from "@/components/reviews/five-t-scorecard";
import { Card } from "@/components/ui/card";
import { reviewApi } from "@/lib/api/client";
import type { ReviewAssignmentDetail, ReviewDraft } from "@/lib/api/types";
import { reviewKeys } from "@/lib/reviews/query-keys";

const statusLabels = {
  ASSIGNED: "Đang thẩm định",
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
  const query = useQuery({
    queryKey: reviewKeys.detail(assignmentId),
    queryFn: () => reviewApi.get(assignmentId),
  });
  const save = useMutation({
    mutationFn: (draft: ReviewDraft) =>
      reviewApi.saveDraft(assignmentId, draft),
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
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-600 hover:text-primary-700"
        href="/reviews"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Trở lại hàng đợi
      </Link>
      <header className="border-l-4 border-l-primary-700 border-y border-r border-[var(--theme-border)] bg-[var(--theme-surface)] px-6 py-6 text-[var(--theme-text)] sm:px-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
              <ClipboardCheck className="size-4" />
              {detail.dossierCode} · Phiên bản {detail.versionNo}
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
              {detail.dossierTitle}
            </h1>
          </div>
          <span className="w-fit rounded-full border border-primary-200 bg-[var(--theme-elevated)] px-3 py-1.5 text-xs font-bold text-primary-800">
            {statusLabels[detail.assignment.status]}
          </span>
        </div>
      </header>

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
            <span className="grid size-8 place-items-center rounded-full bg-[var(--theme-elevated)] font-mono text-xs font-bold text-primary-700">
              {number}
            </span>
            <div>
              <p className="text-sm font-bold">{title}</p>
              <p className="mt-1 text-xs leading-5 text-neutral-500">
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
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-500">
            <Clock3 aria-hidden="true" className="size-4" /> Thời hạn xử lý
          </p>
          <p
            className={`mt-2 font-bold ${deadline.status === "OVERDUE" ? "text-error" : ""}`}
          >
            {deadline.label}
          </p>
          <p className="mt-1 text-xs leading-5 text-neutral-500">
            {deadline.detail}
          </p>
        </article>
        <article className="border-b border-[var(--theme-border)] p-4 sm:border-b-0 sm:border-r sm:p-5">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-500">
            <Files aria-hidden="true" className="size-4" /> Bộ bằng chứng
          </p>
          <p className="mt-2 font-bold">{evidenceCount} tài liệu đã khóa</p>
          <p className="mt-1 text-xs leading-5 text-neutral-500">
            Chỉ dẫn chiếu nội dung thuộc phiên bản {detail.versionNo}
          </p>
        </article>
        <article className="p-4 sm:p-5">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-500">
            <LockKeyhole aria-hidden="true" className="size-4" /> Phạm vi thao
            tác
          </p>
          <p className="mt-2 font-bold">Thẩm định nội bộ</p>
          <p className="mt-1 text-xs leading-5 text-neutral-500">
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
      {terminal ? (
        <Card className="p-8 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-50 text-amber-700">
            <AlertTriangle className="size-6" />
          </span>
          <h2 className="mt-4 text-xl font-bold">Phân công đã kết thúc</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Hồ sơ không còn khả dụng để tiếp tục thẩm định.
          </p>
        </Card>
      ) : null}
      {["IN_PROGRESS", "SUBMITTED"].includes(detail.assignment.status) &&
      detail.snapshotJson ? (
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(20rem,0.76fr)_minmax(34rem,1.24fr)]">
          <div className="space-y-6 xl:sticky xl:top-28">
            {detail.snapshotJson.dossier.summary ? (
              <Card className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                  Tóm tắt của người nộp
                </p>
                <p className="mt-2 text-sm leading-6 text-neutral-700">
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
            <Card className="p-5">
              <p className="flex items-center gap-2 text-xs font-bold text-emerald-700">
                <CheckCircle2 className="size-4" />
                Dấu vân tay phiên bản
              </p>
              <code className="mt-3 block break-all text-xs leading-5 text-neutral-500">
                {detail.canonicalHash}
              </code>
            </Card>
          </div>
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
            requireEvidenceAssessments={detail.snapshotJson.schemaVersion >= 2}
            rubric={detail.snapshotJson.dossier.dossierType?.reviewRubric}
            saveError={save.error}
          />
        </div>
      ) : null}
    </div>
  );
}
