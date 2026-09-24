"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleHelp, LoaderCircle, Send, UsersRound } from "lucide-react";
import { useId, useState } from "react";

import { Card } from "@/components/ui/card";
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
    reason.trim().length >= 20 &&
    !requestHelp.isPending;

  return (
    <Card className="overflow-hidden border-primary-200 bg-[linear-gradient(135deg,var(--theme-surface),var(--theme-elevated))] p-0">
      <div className="border-b border-primary-100 bg-primary-50/60 px-5 py-4 sm:px-6">
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-700 text-white shadow-sm">
            <UsersRound aria-hidden="true" className="size-5" />
          </span>
          <div>
            <h2 className="text-lg font-bold text-neutral-900">
              Phối hợp thẩm định
            </h2>
            <p className="mt-1 text-sm leading-6 text-neutral-600">
              Với hồ sơ phức tạp, hãy nêu rõ phần việc cần thêm chuyên môn.
              Super Admin sẽ cân nhắc và chỉ định moderator phù hợp.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5 sm:p-6">
        {requests.length > 0 ? (
          <div className="space-y-3" aria-label="Lịch sử yêu cầu hỗ trợ">
            {requests.map((item) => (
              <article
                className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
                key={item.id}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-neutral-800">
                      {assistanceStatus[item.status]}
                    </p>
                    <p className="mt-1 text-xs text-neutral-500">
                      {requestDate(item.createdAt)} · cần thêm{" "}
                      {item.requestedReviewerCount} moderator
                    </p>
                  </div>
                  <span
                    className={
                      item.status === "PENDING"
                        ? "rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900"
                        : item.status === "APPROVED"
                          ? "rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-900"
                          : "rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-700"
                    }
                  >
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-neutral-700">
                  {item.reason}
                </p>
                {item.decisionReason ? (
                  <p className="mt-3 border-t border-[var(--theme-border)] pt-3 text-sm leading-6 text-neutral-600">
                    <span className="font-bold text-neutral-800">
                      Phản hồi:
                    </span>{" "}
                    {item.decisionReason}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}

        {canRequest && !pending ? (
          <form
            className="space-y-4 rounded-xl border border-dashed border-primary-300 bg-white/60 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (canSubmit) requestHelp.mutate();
            }}
          >
            <div className="flex items-center gap-2 text-sm font-bold text-neutral-800">
              <CircleHelp
                aria-hidden="true"
                className="size-4 text-primary-700"
              />
              Gửi yêu cầu hỗ trợ
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
            <p className="text-xs leading-5 text-neutral-500">
              Tối thiểu 20 ký tự. Bạn chỉ có thể có một yêu cầu đang chờ xử lý
              cho mỗi phân công.
            </p>
          </form>
        ) : null}

        {!canRequest && requests.length === 0 ? (
          <p className="text-sm text-neutral-500">
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
    </Card>
  );
}
