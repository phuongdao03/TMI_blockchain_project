"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  LoaderCircle,
  UserCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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

const routingReason = "Hệ thống chuyển hồ sơ đến người kiểm duyệt.";

function decisionErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message.includes("complete submitted review")) {
    return "Hệ thống chưa ghi nhận báo cáo đã hoàn tất. Hãy tải lại trang và thử lại.";
  }
  if (message.includes("Every assigned reviewer")) {
    return "Vẫn còn người kiểm duyệt chưa gửi báo cáo hoặc khai báo xung đột lợi ích.";
  }
  if (message.includes("integrity") || message.includes("reverified")) {
    return "Bằng chứng cần được hệ thống kiểm tra lại tính toàn vẹn trước khi phê duyệt.";
  }
  if (message.includes("UNDER_REVIEW")) {
    return "Trạng thái hồ sơ đã thay đổi. Hãy tải lại trang trước khi ra quyết định.";
  }
  return "Chưa thể ghi nhận quyết định. Nội dung trên màn hình vẫn được giữ lại; vui lòng thử lại.";
}

function decisionRequestId(error: unknown): string | undefined {
  if (
    typeof error === "object" &&
    error !== null &&
    "requestId" in error &&
    typeof error.requestId === "string"
  ) {
    return error.requestId;
  }
  return undefined;
}

function ReviewReport({ item }: { item: AdminReviewAssignment }) {
  const { assignment, review, reviewerEmail } = item;
  return (
    <article className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:p-5">
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
  const [reviewerId, setReviewerId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [finalReason, setFinalReason] = useState("");
  const [confirmNoConflict, setConfirmNoConflict] = useState(false);
  const [activeDecision, setActiveDecision] =
    useState<AdminDossierDecision | null>(null);
  const canChooseReviewer = ["SUBMITTED", "PRECHECK", "UNDER_REVIEW"].includes(
    dossier.status,
  );
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
      if (dossier.status === "SUBMITTED") {
        await adminReviewApi.startPrecheck(dossier.dossierId, routingReason);
      }
      if (dossier.status === "SUBMITTED" || dossier.status === "PRECHECK") {
        await adminReviewApi.passPrecheck(dossier.dossierId, routingReason);
      }
      return adminReviewApi.assign(
        dossier.dossierId,
        [reviewerId],
        dueAt ? new Date(dueAt).toISOString() : undefined,
      );
    },
    onSettled: refresh,
  });
  const busy = handoff.isPending;
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
  });
  useEffect(() => {
    if (!decide.isSuccess || !decide.data) {
      return;
    }
    const destination =
      decide.data.status === "APPROVED" ? "/blockchain" : "/admin/reviews";
    const timer = window.setTimeout(() => router.push(destination), 850);
    return () => window.clearTimeout(timer);
  }, [decide.data, decide.isSuccess, router]);
  const requestFinalSupplement = useMutation({
    mutationFn: () =>
      adminReviewApi.requestSupplement(dossier.dossierId, finalReason),
    onSuccess: async () => {
      await refresh();
    },
  });
  useEffect(() => {
    if (!requestFinalSupplement.isSuccess) {
      return;
    }
    const timer = window.setTimeout(() => router.push("/admin/reviews"), 850);
    return () => window.clearTimeout(timer);
  }, [requestFinalSupplement.isSuccess, router]);
  const submitDecision = (decision: AdminDossierDecision) => {
    setActiveDecision(decision);
    decide.reset();
    decide.mutate(decision);
  };
  const submitSupplementRequest = () => {
    setActiveDecision("REQUEST_MORE_INFO");
    requestFinalSupplement.reset();
    requestFinalSupplement.mutate();
  };
  const decisionPending = decide.isPending || requestFinalSupplement.isPending;
  const decisionSucceeded =
    decide.isSuccess || requestFinalSupplement.isSuccess;
  const decisionLocked = decisionPending || decisionSucceeded;
  const decisionError = decide.error ?? requestFinalSupplement.error;
  const requestId = decisionRequestId(decisionError);

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
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

        {canChooseReviewer ? (
          <div className="mt-5 grid gap-4 md:grid-cols-2">
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
                disabled={!reviewerId || busy}
                onClick={() => handoff.mutate()}
                type="button"
              >
                {handoff.isPending ? "Đang phân công…" : "Phân công kiểm duyệt"}
              </button>
            </div>
          </div>
        ) : null}

        {handoff.isError ? (
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
        <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
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
                Admin xem kết luận của người kiểm duyệt trước khi quyết định
                cuối.
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

      {dossier.assignments.length > 0 ? (
        <section className="admin-decision-panel rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700">
              <FileCheck2 aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold sm:text-xl">
                Quyết định cuối của Admin
              </h2>
              <p className="mt-1 text-sm leading-6 text-neutral-500">
                Đọc báo cáo của người kiểm duyệt, ghi rõ căn cứ và chọn quyết
                định cuối.
              </p>
            </div>
          </div>
          {!isDecisionReady ? (
            <div
              className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
              role="status"
            >
              <Clock3 aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <p>
                Chức năng ra quyết định sẽ mở khi tất cả phân công đã hoàn tất.
              </p>
            </div>
          ) : null}
          <label className="mt-5 block text-sm font-semibold">
            Lý do quyết định cuối
            <textarea
              aria-describedby="final-reason-help"
              className="mt-2 min-h-28 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-3 leading-6"
              disabled={!isDecisionReady || decisionLocked}
              maxLength={2000}
              onChange={(event) => setFinalReason(event.target.value)}
              placeholder={
                isDecisionReady
                  ? "Nêu căn cứ dựa trên báo cáo của người kiểm duyệt"
                  : "Đang chờ báo cáo kiểm duyệt hoàn tất"
              }
              value={finalReason}
            />
          </label>
          <div
            className="mt-2 flex items-start justify-between gap-4 text-xs text-neutral-500"
            id="final-reason-help"
          >
            <span>Căn cứ nên nêu rõ báo cáo và bằng chứng đã xem.</span>
            <span className="shrink-0 tabular-nums">
              {finalReason.length}/2000
            </span>
          </div>
          <label className="mt-4 flex items-start gap-3 text-sm font-medium">
            <input
              checked={confirmNoConflict}
              className="mt-0.5 h-4 w-4 accent-primary-700"
              disabled={!isDecisionReady || decisionLocked}
              onChange={(event) => setConfirmNoConflict(event.target.checked)}
              type="checkbox"
            />
            <span>
              Tôi xác nhận đã đọc đầy đủ báo cáo kiểm duyệt và không có xung đột
              lợi ích khi ra quyết định cuối.
            </span>
          </label>
          <div className="admin-decision-panel__actions mt-5 grid gap-3 sm:flex sm:flex-wrap">
            <button
              className="admin-decision-panel__button admin-decision-panel__button--primary min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={
                !isDecisionReady ||
                !finalReason.trim() ||
                !confirmNoConflict ||
                decisionLocked
              }
              onClick={() => submitDecision("APPROVE")}
              type="button"
            >
              {decisionPending && activeDecision === "APPROVE"
                ? "Đang phê duyệt…"
                : "Phê duyệt hồ sơ"}
            </button>
            <button
              className="admin-decision-panel__button min-h-11 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-5 font-bold disabled:cursor-not-allowed disabled:opacity-50"
              disabled={
                !isDecisionReady || !finalReason.trim() || decisionLocked
              }
              onClick={submitSupplementRequest}
              type="button"
            >
              {decisionPending && activeDecision === "REQUEST_MORE_INFO"
                ? "Đang gửi yêu cầu…"
                : "Yêu cầu bổ sung"}
            </button>
            <button
              className="admin-decision-panel__button min-h-11 rounded-xl border border-red-300 px-5 font-bold text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={
                !isDecisionReady ||
                !finalReason.trim() ||
                !confirmNoConflict ||
                decisionLocked
              }
              onClick={() => submitDecision("REJECT")}
              type="button"
            >
              {decisionPending && activeDecision === "REJECT"
                ? "Đang từ chối…"
                : "Từ chối hồ sơ"}
            </button>
          </div>
          {decisionPending ? (
            <div
              aria-live="polite"
              className="admin-decision-status admin-decision-status--pending mt-4"
              role="status"
            >
              <LoaderCircle
                aria-hidden="true"
                className="size-5 animate-spin"
              />
              <div>
                <p
                  className="t-shimmer font-bold"
                  data-text="Đang ghi nhận quyết định…"
                >
                  Đang ghi nhận quyết định…
                </p>
                <p className="mt-1 text-sm text-neutral-500">
                  Hệ thống đang tạo biên bản và cập nhật trạng thái hồ sơ. Không
                  đóng trang này.
                </p>
              </div>
            </div>
          ) : null}
          {decisionSucceeded ? (
            <div
              aria-live="polite"
              className="admin-decision-status admin-decision-status--success mt-4"
              role="status"
            >
              <span
                aria-hidden="true"
                className="t-success-check admin-decision-status__check"
                data-state="in"
              >
                <svg fill="none" viewBox="0 0 24 24">
                  <path d="M4 12.5 9 17 20 6" />
                </svg>
              </span>
              <div>
                <p className="font-bold">
                  {activeDecision === "REQUEST_MORE_INFO"
                    ? "Đã gửi yêu cầu bổ sung"
                    : "Đã ghi nhận quyết định"}
                </p>
                <p className="mt-1 text-sm">
                  Đang chuyển sang bước tiếp theo của quy trình.
                </p>
              </div>
            </div>
          ) : null}
          {decide.isError || requestFinalSupplement.isError ? (
            <div className="t-input-wrap is-error mt-4" role="alert">
              <div className="t-input is-error is-shaking review-workspace__error flex items-start gap-3 rounded-xl border p-4 text-sm">
                <AlertTriangle
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0"
                />
                <div>
                  <p className="font-bold">Chưa thể ghi nhận quyết định</p>
                  <p className="mt-1 leading-6">
                    {decisionErrorMessage(decisionError)}
                  </p>
                  {requestId ? (
                    <p className="mt-2 font-mono text-xs font-medium opacity-80">
                      Mã tra cứu: {requestId}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
