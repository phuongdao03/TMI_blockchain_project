"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleHelp, LoaderCircle, Send, UsersRound } from "lucide-react";
import { useId, useState } from "react";

import { WorkflowNextStep } from "@/components/ui/workflow-next-step";
import { reviewApi } from "@/lib/api/client";
import type { ReviewAssistanceRequest } from "@/lib/api/types";
import { reviewKeys } from "@/lib/reviews/query-keys";

const assistanceStatus = {
  PENDING: "Đang chờ Admin xử lý",
  APPROVED: "Đã bổ sung người thẩm định",
  DECLINED: "Chưa được phê duyệt",
} as const;

function requestDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ReviewAssistancePanel({
  assignmentId,
  canRequest,
  requests,
}: {
  assignmentId: string;
  canRequest: boolean;
  requests: ReviewAssistanceRequest[];
}) {
  const queryClient = useQueryClient();
  const reasonId = useId();
  const countId = useId();
  const [reason, setReason] = useState("");
  const [requestedReviewerCount, setRequestedReviewerCount] = useState(1);
  const pending = requests.find((item) => item.status === "PENDING");
  const requestHelp = useMutation({
    mutationFn: () =>
      reviewApi.requestAssistance(assignmentId, {
        reason: reason.trim(),
        requestedReviewerCount,
      }),
    onSuccess: async () => {
      setReason("");
      await queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(assignmentId),
      });
    },
  });
  const canSubmit =
    canRequest &&
    !pending &&
    !requestHelp.isSuccess &&
    reason.trim().length >= 20 &&
    !requestHelp.isPending;

  return (
    <section
      className="review-assistance scroll-mt-24 border-t border-[var(--theme-border)] pt-6 text-[var(--theme-text)]"
      id="review-assistance"
    >
      <div>
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--theme-elevated)] text-[var(--theme-accent)]">
            <UsersRound aria-hidden="true" className="size-5" />
          </span>
          <div>
            <h2 className="text-lg font-bold text-[var(--theme-text)]">
              Phối hợp thẩm định
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
              Với hồ sơ phức tạp, hãy nêu rõ phần việc cần thêm chuyên môn.
              Super Admin sẽ cân nhắc và chỉ định moderator phù hợp.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-4 pl-0 sm:pl-12">
        {requestHelp.isSuccess ? (
          <WorkflowNextStep
            action={{ href: "#review-form", label: "Tiếp tục báo cáo" }}
            description="Tiếp tục kiểm tra hồ sơ trong lúc Admin xem yêu cầu và chỉ định thêm người kiểm duyệt. Trạng thái sẽ cập nhật tại đây."
            title="Đã gửi yêu cầu hỗ trợ cho Admin"
            tone="success"
          />
        ) : null}
        {requests.length > 0 ? (
          <div
            className="divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)]"
            aria-label="Lịch sử yêu cầu hỗ trợ"
          >
            {requests.map((item) => (
              <article className="py-4" key={item.id}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-[var(--theme-text)]">
                      {assistanceStatus[item.status]}
                    </p>
                    <p className="mt-1 text-xs text-[var(--theme-muted)]">
                      {requestDate(item.createdAt)} · cần thêm{" "}
                      {item.requestedReviewerCount} moderator
                    </p>
                  </div>
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--theme-text)]">
                  {item.reason}
                </p>
                {item.decisionReason ? (
                  <p className="mt-3 border-t border-[var(--theme-border)] pt-3 text-sm leading-6 text-[var(--theme-muted)]">
                    <span className="font-bold text-[var(--theme-text)]">
                      Phản hồi:
                    </span>{" "}
                    {item.decisionReason}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}

        {canRequest && !pending && !requestHelp.isSuccess ? (
          <details className="group border-t border-[var(--theme-border)] pt-3">
            <summary className="min-h-11 cursor-pointer font-semibold text-[var(--theme-accent)] marker:text-[var(--theme-accent)]">
              Gửi yêu cầu hỗ trợ
            </summary>
            <form
              className="mt-3 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (canSubmit) requestHelp.mutate();
              }}
            >
              <div className="flex items-center gap-2 text-sm font-bold text-[var(--theme-text)]">
                <CircleHelp
                  aria-hidden="true"
                  className="size-4 text-primary-700"
                />
                Nêu rõ phần việc cần thêm chuyên môn
              </div>
              <label className="block text-sm font-semibold" htmlFor={reasonId}>
                Lý do cần hỗ trợ
                <textarea
                  className="mt-2 min-h-28 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm leading-6 outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
                  disabled={requestHelp.isPending}
                  id={reasonId}
                  maxLength={2000}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Mô tả độ phức tạp, phần cần đối chiếu hoặc chuyên môn cần bổ sung…"
                  value={reason}
                />
              </label>
              <div className="flex flex-wrap items-end justify-between gap-4">
                <label className="text-sm font-semibold" htmlFor={countId}>
                  Số moderator cần thêm
                  <select
                    className="mt-2 block min-h-11 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 font-medium outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
                    disabled={requestHelp.isPending}
                    id={countId}
                    onChange={(event) =>
                      setRequestedReviewerCount(Number(event.target.value))
                    }
                    value={requestedReviewerCount}
                  >
                    {Array.from({ length: 10 }, (_, index) => index + 1).map(
                      (count) => (
                        <option key={count} value={count}>
                          {count} người
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <button
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary-700 px-4 text-sm font-bold text-white transition hover:bg-primary-800 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!canSubmit}
                  type="submit"
                >
                  {requestHelp.isPending ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="size-4 animate-spin"
                    />
                  ) : (
                    <Send aria-hidden="true" className="size-4" />
                  )}
                  Gửi Admin
                </button>
              </div>
              <p className="text-xs leading-5 text-[var(--theme-muted)]">
                Tối thiểu 20 ký tự. Bạn chỉ có thể có một yêu cầu đang chờ xử lý
                cho mỗi phân công.
              </p>
            </form>
          </details>
        ) : null}

        {!canRequest && requests.length === 0 ? (
          <p className="text-sm text-[var(--theme-muted)]">
            Yêu cầu hỗ trợ chỉ mở khi phân công đang được thực hiện.
          </p>
        ) : null}
        {requestHelp.isError ? (
          <p
            className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800"
            role="alert"
          >
            {requestHelp.error.message ||
              "Chưa thể gửi yêu cầu. Vui lòng thử lại."}
          </p>
        ) : null}
      </div>
    </section>
  );
}
