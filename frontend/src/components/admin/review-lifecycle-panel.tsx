"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileCheck2, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { adminReviewApi, staffAccountsApi } from "@/lib/api/client";
import type {
  AdminReviewAssignment,
  AdminDossierDecision,
  AdminReviewDossierDetail,
  ReviewRecommendation,
} from "@/lib/api/types";

const recommendationLabels: Record<ReviewRecommendation, string> = {
  APPROVE: "Đề nghị phê duyệt",
  SUPPLEMENT: "Đề nghị bổ sung",
  REJECT: "Đề nghị từ chối",
};

const assignmentLabels = {
  ASSIGNED: "Chờ tiếp nhận",
  IN_PROGRESS: "Đang kiểm duyệt",
  CONFLICTED: "Đã báo xung đột",
  SUBMITTED: "Đã gửi báo cáo",
  CANCELLED: "Đã hủy",
} as const;

function ReviewReport({ item }: { item: AdminReviewAssignment }) {
  const { assignment, review, reviewerEmail } = item;
  return (
    <article className="rounded-xl border border-[var(--theme-border)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-bold">{reviewerEmail}</p>
          <p className="mt-1 text-sm text-neutral-500">
            {assignmentLabels[assignment.status]}
          </p>
        </div>
        {review?.recommendation ? (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">
            {recommendationLabels[review.recommendation]}
          </span>
        ) : null}
      </div>
      {review ? (
        <dl className="mt-4 grid gap-4 border-t border-[var(--theme-border)] pt-4 md:grid-cols-2">
          {review.totalScore !== null ? (
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                Tổng điểm
              </dt>
              <dd className="mt-1 font-bold">{review.totalScore}/100</dd>
            </div>
          ) : null}
          {review.submittedAt ? (
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                Gửi lúc
              </dt>
              <dd className="mt-1">
                {new Date(review.submittedAt).toLocaleString("vi-VN")}
              </dd>
            </div>
          ) : null}
          {review.applicantFeedback ? (
            <div className="md:col-span-2">
              <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                Nhận xét
              </dt>
              <dd className="mt-1 whitespace-pre-wrap">
                {review.applicantFeedback}
              </dd>
            </div>
          ) : null}
          {review.privateNote ? (
            <div className="md:col-span-2">
              <dt className="text-xs font-bold uppercase tracking-wide text-neutral-500">
                Ghi chú nội bộ
              </dt>
              <dd className="mt-1 whitespace-pre-wrap">{review.privateNote}</dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="mt-4 text-sm text-neutral-500">
          Reviewer chưa gửi báo cáo. Admin sẽ nhận thông báo ngay khi hoàn tất.
        </p>
      )}
    </article>
  );
}

export function ReviewLifecyclePanel({
  dossier,
}: {
  dossier: AdminReviewDossierDetail;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [reason, setReason] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [finalReason, setFinalReason] = useState("");
  const [confirmNoConflict, setConfirmNoConflict] = useState(false);
  const canChooseReviewer =
    dossier.status === "PRECHECK" || dossier.status === "UNDER_REVIEW";
  const reviewers = useQuery({
    queryKey: ["staff-accounts", "active-reviewers"],
    queryFn: () =>
      staffAccountsApi.list({
        role: "MODERATOR",
        status: "ACTIVE",
        pageSize: 100,
      }),
    enabled: canChooseReviewer,
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin-review-dossiers"] }),
      queryClient.invalidateQueries({
        queryKey: ["admin-review-dossier", dossier.dossierId],
      }),
    ]);
  };
  const handoff = useMutation({
    mutationFn: async () => {
      if (dossier.status === "PRECHECK") {
        await adminReviewApi.passPrecheck(dossier.dossierId, reason);
      }
      return adminReviewApi.assign(
        dossier.dossierId,
        [reviewerId],
        dueAt ? new Date(dueAt).toISOString() : undefined,
      );
    },
    onSettled: refresh,
  });
  const transition = useMutation({
    mutationFn: (action: "start" | "supplement") =>
      action === "start"
        ? adminReviewApi.startPrecheck(dossier.dossierId, reason)
        : adminReviewApi.requestSupplement(dossier.dossierId, reason),
    onSuccess: async (_, action) => {
      if (action === "supplement") router.push("/admin/reviews");
      await refresh();
    },
  });
  const busy = handoff.isPending || transition.isPending;
  const assignedIds = new Set(
    dossier.assignments.map((item) => item.assignment.reviewerUserId),
  );
  const isDecisionReady =
    dossier.assignments.length > 0 &&
    dossier.assignments.some((item) => item.review?.submittedAt) &&
    dossier.assignments.every((item) =>
      ["SUBMITTED", "CONFLICTED", "CANCELLED"].includes(item.assignment.status),
    );
  const decide = useMutation({
    mutationFn: (decision: AdminDossierDecision) =>
      adminReviewApi.decide(
        dossier.dossierId,
        decision,
        finalReason,
        confirmNoConflict,
      ),
    onSuccess: (result) => {
      router.push(
        result.status === "APPROVED" ? "/blockchain" : "/admin/reviews",
      );
    },
  });
  const requestFinalSupplement = useMutation({
    mutationFn: () =>
      adminReviewApi.requestSupplement(dossier.dossierId, finalReason),
    onSuccess: async () => {
      await refresh();
      router.push("/admin/reviews");
    },
  });

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
        <div className="flex items-start gap-3">
          <UserCheck className="mt-0.5 size-5 text-primary-700" />
          <div>
            <h2 className="text-xl font-bold">Phân công người kiểm duyệt</h2>
            <p className="mt-1 text-sm text-neutral-500">
              Chỉ tài khoản đang hoạt động với vai trò Người kiểm duyệt mới xuất
              hiện trong danh sách.
            </p>
          </div>
        </div>

        {dossier.status === "SUBMITTED" ? (
          <div className="mt-5 space-y-4">
            <label className="block text-sm font-semibold">
              Ghi chú tiếp nhận
              <textarea
                className="mt-2 min-h-24 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3"
                onChange={(event) => setReason(event.target.value)}
                value={reason}
              />
            </label>
            <button
              className="min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:opacity-50"
              disabled={!reason.trim() || busy}
              onClick={() => transition.mutate("start")}
              type="button"
            >
              {transition.isPending
                ? "Đang tiếp nhận…"
                : "Tiếp nhận và bắt đầu sơ kiểm"}
            </button>
          </div>
        ) : canChooseReviewer ? (
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {dossier.status === "PRECHECK" ? (
              <label className="block text-sm font-semibold md:col-span-2">
                Ghi chú sơ kiểm
                <textarea
                  className="mt-2 min-h-24 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3"
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Ghi kết quả đọc và đối chiếu hồ sơ"
                  value={reason}
                />
              </label>
            ) : null}
            <label className="text-sm font-semibold">
              Người kiểm duyệt
              <select
                className="mt-2 min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
                onChange={(event) => setReviewerId(event.target.value)}
                value={reviewerId}
              >
                <option value="">Chọn người kiểm duyệt</option>
                {reviewers.data?.data
                  .filter((reviewer) => !assignedIds.has(reviewer.id))
                  .map((reviewer) => (
                    <option key={reviewer.id} value={reviewer.id}>
                      {reviewer.email}
                    </option>
                  ))}
              </select>
            </label>
            <label className="text-sm font-semibold">
              Hạn xử lý (không bắt buộc)
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
                onChange={(event) => setDueAt(event.target.value)}
                type="datetime-local"
                value={dueAt}
              />
            </label>
            <div className="flex flex-wrap gap-3 md:col-span-2">
              <button
                className="min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:opacity-50"
                disabled={
                  !reviewerId ||
                  busy ||
                  (dossier.status === "PRECHECK" && !reason.trim())
                }
                onClick={() => handoff.mutate()}
                type="button"
              >
                {handoff.isPending
                  ? "Đang phân công…"
                  : dossier.status === "PRECHECK"
                    ? "Đạt sơ kiểm và phân công"
                    : "Phân công người kiểm duyệt"}
              </button>
              <button
                className="min-h-11 rounded-xl border border-red-300 px-5 font-bold text-red-700 disabled:opacity-50"
                disabled={!reason.trim() || busy}
                onClick={() => transition.mutate("supplement")}
                type="button"
              >
                Yêu cầu bổ sung
              </button>
            </div>
          </div>
        ) : null}

        {handoff.isError || transition.isError ? (
          <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
            Chưa thể cập nhật hồ sơ. Kiểm tra dữ liệu và thử lại.
          </p>
        ) : null}
        {handoff.isSuccess ? (
          <p
            className="mt-4 text-sm font-semibold text-green-700"
            role="status"
          >
            Đã phân công và gửi thông báo cho người kiểm duyệt.
          </p>
        ) : null}
      </section>

      {dossier.assignments.length > 0 ? (
        <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
          <div className="flex items-start gap-3">
            {dossier.assignments.every(
              (item) =>
                item.assignment.status === "SUBMITTED" ||
                item.assignment.status === "CONFLICTED",
            ) ? (
              <CheckCircle2 className="mt-0.5 size-5 text-green-700" />
            ) : (
              <Clock3 className="mt-0.5 size-5 text-amber-700" />
            )}
            <div>
              <h2 className="text-xl font-bold">Báo cáo kiểm duyệt</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Admin xem kết luận của reviewer trước khi quyết định cuối.
              </p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {dossier.assignments.map((item) => (
              <ReviewReport item={item} key={item.assignment.id} />
            ))}
          </div>
        </section>
      ) : (
        <section className="rounded-2xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-neutral-500">
          <FileCheck2 className="mb-3 size-5" />
          Chưa có phân công. Chọn một người kiểm duyệt để bắt đầu quy trình.
        </section>
      )}

      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
        <h2 className="text-xl font-bold">Quyết định cuối của Admin</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Chỉ mở sau khi mọi người kiểm duyệt đã hoàn tất. Quyết định được lưu
          thành biên bản trước khi chuyển sang ký blockchain.
        </p>
        <label className="mt-5 block text-sm font-semibold">
          Lý do quyết định cuối
          <textarea
            className="mt-2 min-h-24 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3"
            disabled={!isDecisionReady || decide.isPending}
            onChange={(event) => setFinalReason(event.target.value)}
            placeholder={
              isDecisionReady
                ? "Nêu căn cứ dựa trên báo cáo và tài liệu"
                : "Đang chờ báo cáo kiểm duyệt hoàn tất"
            }
            value={finalReason}
          />
        </label>
        <label className="mt-4 flex items-start gap-3 text-sm font-medium">
          <input
            checked={confirmNoConflict}
            className="mt-0.5 h-4 w-4 accent-primary-700"
            disabled={!isDecisionReady || decide.isPending}
            onChange={(event) => setConfirmNoConflict(event.target.checked)}
            type="checkbox"
          />
          <span>
            Tôi xác nhận đã đọc báo cáo, đối chiếu tài liệu và không có xung đột
            lợi ích.
          </span>
        </label>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className="min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:opacity-50"
            disabled={
              !isDecisionReady ||
              !finalReason.trim() ||
              !confirmNoConflict ||
              decide.isPending
            }
            onClick={() => decide.mutate("APPROVE")}
            type="button"
          >
            Phê duyệt hồ sơ
          </button>
          <button
            className="min-h-11 rounded-xl border border-[var(--theme-border)] px-5 font-bold disabled:opacity-50"
            disabled={
              !isDecisionReady ||
              !finalReason.trim() ||
              decide.isPending ||
              requestFinalSupplement.isPending
            }
            onClick={() => requestFinalSupplement.mutate()}
            type="button"
          >
            Yêu cầu bổ sung
          </button>
          <button
            className="min-h-11 rounded-xl border border-red-300 px-5 font-bold text-red-700 disabled:opacity-50"
            disabled={
              !isDecisionReady ||
              !finalReason.trim() ||
              !confirmNoConflict ||
              decide.isPending
            }
            onClick={() => decide.mutate("REJECT")}
            type="button"
          >
            Từ chối hồ sơ
          </button>
        </div>
        {decide.isError || requestFinalSupplement.isError ? (
          <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
            Chưa thể ghi nhận quyết định. Hãy kiểm tra báo cáo và thử lại.
          </p>
        ) : null}
      </section>
    </div>
  );
}
