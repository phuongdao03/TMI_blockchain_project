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

import { ConflictGate } from "@/components/reviews/conflict-gate";
import { EvidenceViewer } from "@/components/reviews/evidence-viewer";
import { FiveTScorecard } from "@/components/reviews/five-t-scorecard";
import { Card } from "@/components/ui/card";
import { reviewApi } from "@/lib/api/client";
import type { ReviewAssignmentDetail, ReviewDraft } from "@/lib/api/types";
import { reviewKeys } from "@/lib/reviews/query-keys";

const statusLabels = {
  ASSIGNED: "Chờ xác nhận xung đột",
  IN_PROGRESS: "Đang thẩm định",
  CONFLICTED: "Đã báo xung đột",
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
      label: "Đã quá SLA",
      detail: `${dateLabel} · quá hạn ${Math.abs(differenceHours)} giờ`,
    };
  }
  return {
    status: "ON_TRACK" as const,
    label: differenceHours <= 24 ? "Sắp đến hạn" : "Trong SLA",
    detail: `${dateLabel} · còn ${differenceHours} giờ`,
  };
}

export function ReviewWorkspace({ assignmentId }: { assignmentId: string }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: reviewKeys.detail(assignmentId),
    queryFn: () => reviewApi.get(assignmentId),
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: reviewKeys.detail(assignmentId),
    });
  const conflict = useMutation({
    mutationFn: (input: { hasConflict: boolean; reason: string | null }) =>
      reviewApi.declareConflict(assignmentId, input),
    onSuccess: refresh,
  });
  const save = useMutation({
    mutationFn: (draft: ReviewDraft) =>
      reviewApi.saveDraft(assignmentId, draft),
    onSuccess: (review) => {
      queryClient.setQueryData<ReviewAssignmentDetail>(
        reviewKeys.detail(assignmentId),
        (current) => (current ? { ...current, review } : current),
      );
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
    <div className="mx-auto max-w-[92rem] space-y-6">
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-600 hover:text-primary-700"
        href="/reviews"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        Trở lại hàng đợi
      </Link>
      <header className="rounded-3xl bg-ink-950 p-6 text-white shadow-xl shadow-slate-950/10 sm:p-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
              <ClipboardCheck className="size-4" />
              {detail.dossierCode} · Phiên bản {detail.versionNo}
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
              {detail.dossierTitle}
            </h1>
          </div>
          <span className="w-fit rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold">
            {statusLabels[detail.assignment.status]}
          </span>
        </div>
      </header>

      <section
        aria-label="Quy trình thẩm định"
        className="grid overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] sm:grid-cols-3 xl:grid-cols-6"
      >
        {[
          ["01", "Độc lập", "Khai báo xung đột"],
          ["02", "Kiểm tra", "Khóa phiên bản & tài liệu"],
          ["03", "Chấm 5T", "Điểm neo & căn cứ"],
          ["04", "Phát hiện", "Rủi ro & hướng xử lý"],
          ["05", "Kiến nghị", "Qua cổng quyết định"],
          ["06", "Khóa phiếu", "Xác nhận & gửi một lần"],
        ].map(([number, title, description]) => (
          <article
            className="border-b border-[var(--theme-border)] p-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
            key={number}
          >
            <p className="font-mono text-xs font-bold text-primary-700">
              {number}
            </p>
            <p className="mt-2 text-sm font-bold">{title}</p>
            <p className="mt-1 text-xs leading-5 text-neutral-500">
              {description}
            </p>
          </article>
        ))}
      </section>

      <section
        aria-label="Thông tin kiểm soát phiên thẩm định"
        className="grid overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] sm:grid-cols-3"
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
          <p className="mt-2 font-bold">Thẩm định độc lập</p>
          <p className="mt-1 text-xs leading-5 text-neutral-500">
            Không thể sửa hồ sơ hoặc đưa ra quyết định cuối cùng
          </p>
        </article>
      </section>

      {conflict.error ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"
          role="alert"
        >
          Không thể ghi nhận xác nhận xung đột. Vui lòng thử lại.
        </p>
      ) : null}
      {save.error || submit.error ? (
        <p
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"
          role="alert"
        >
          Không thể lưu hoặc gửi phiếu thẩm định. Nội dung vẫn còn trên màn
          hình; vui lòng thử lại.
        </p>
      ) : null}
      {detail.assignment.status === "ASSIGNED" ? (
        <ConflictGate
          isPending={conflict.isPending}
          onDeclare={async (input) => {
            await conflict.mutateAsync(input);
          }}
        />
      ) : null}
      {terminal ? (
        <Card className="p-8 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-50 text-amber-700">
            <AlertTriangle className="size-6" />
          </span>
          <h2 className="mt-4 text-xl font-bold">Phân công đã kết thúc</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Hồ sơ không còn khả dụng cho thao tác chấm điểm.
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
            <EvidenceViewer evidences={detail.snapshotJson.evidences ?? []} />
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
            rubric={detail.snapshotJson.dossier.dossierType?.reviewRubric}
          />
        </div>
      ) : null}
    </div>
  );
}
