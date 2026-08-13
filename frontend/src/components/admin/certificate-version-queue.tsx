"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  Check,
  Clock3,
  LoaderCircle,
  RefreshCw,
  X,
} from "lucide-react";
import { useState } from "react";

import { Feedback } from "@/components/ui/feedback";
import { certificateVersionRequestApi } from "@/lib/api/client";
import type { CertificateVersion } from "@/lib/api/types";

const statusLabels: Record<string, string> = {
  PENDING_APPROVAL: "Chờ xem xét",
  ANCHOR_PENDING: "Đang hoàn tất phát hành",
  FAILED: "Cần xử lý lại",
};

function date(value: string | null) {
  if (!value) return "Chưa cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function CertificateVersionQueue() {
  const queryClient = useQueryClient();
  const [rejecting, setRejecting] = useState<CertificateVersion | null>(null);
  const [reason, setReason] = useState("");
  const queue = useQuery({
    queryKey: ["admin", "certificate-version-requests"],
    queryFn: () => certificateVersionRequestApi.list(1, 50),
  });
  const decision = useMutation({
    mutationFn: ({
      versionId,
      input,
    }: {
      versionId: string;
      input: { decision: "APPROVE" } | { decision: "REJECT"; reason: string };
    }) => certificateVersionRequestApi.decide(versionId, input),
    onSuccess: async () => {
      setRejecting(null);
      setReason("");
      await queryClient.invalidateQueries({
        queryKey: ["admin", "certificate-version-requests"],
      });
    },
  });

  if (queue.isPending) {
    return (
      <div className="grid min-h-72 place-items-center" role="status">
        <span className="flex items-center gap-2 text-sm font-bold text-neutral-600">
          <LoaderCircle className="size-5 animate-spin" /> Đang tải hàng chờ…
        </span>
      </div>
    );
  }
  if (queue.error || !queue.data) {
    return (
      <Feedback title="Không thể tải hàng chờ" tone="error">
        Vui lòng thử lại sau.
      </Feedback>
    );
  }
  const metrics = [
    {
      label: "Chờ xem xét",
      value: queue.data.data.filter(
        (item) => item.status === "PENDING_APPROVAL",
      ).length,
      icon: Clock3,
    },
    {
      label: "Đang phát hành",
      value: queue.data.data.filter((item) => item.status === "ANCHOR_PENDING")
        .length,
      icon: BadgeCheck,
    },
    {
      label: "Cần xử lý lại",
      value: queue.data.data.filter((item) => item.status === "FAILED").length,
      icon: RefreshCw,
    },
  ];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-3">
        {metrics.map(({ icon: Icon, label, value }) => (
          <article
            className="border-t-2 border-primary-600 bg-white px-5 py-6"
            key={label}
          >
            <Icon className="size-5 text-primary-700" />
            <p className="mt-5 text-3xl font-bold">{value}</p>
            <p className="mt-1 text-sm text-neutral-600">{label}</p>
          </article>
        ))}
      </section>

      {queue.data.data.length === 0 ? (
        <section className="border border-dashed border-neutral-300 bg-white px-6 py-16 text-center">
          <Check className="mx-auto size-10 text-emerald-600" />
          <h2 className="mt-4 text-xl font-bold">Hàng chờ đã được xử lý</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Chưa có yêu cầu cập nhật chứng thư cần xem xét.
          </p>
        </section>
      ) : (
        <section className="overflow-hidden border border-neutral-200 bg-white">
          <div className="border-b border-neutral-200 px-5 py-4">
            <h2 className="font-bold">Yêu cầu đang xử lý</h2>
            <p className="mt-1 text-sm text-neutral-500">
              Đọc lý do, đối chiếu hồ sơ đã duyệt rồi mới đưa ra quyết định.
            </p>
          </div>
          <div className="divide-y divide-neutral-200">
            {queue.data.data.map((item) => (
              <article
                className="grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-center"
                key={item.id}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>Chứng thư · phiên bản {item.versionNo}</strong>
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">
                      {statusLabels[item.status] ?? "Đang xử lý"}
                    </span>
                  </div>
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
                    {item.changeReason}
                  </p>
                  <p className="mt-2 text-xs text-neutral-400">
                    Tiếp nhận {date(item.requestedAt)}
                  </p>
                </div>
                {item.status === "PENDING_APPROVAL" ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white disabled:opacity-50"
                      disabled={decision.isPending}
                      onClick={() =>
                        decision.mutate({
                          versionId: item.id,
                          input: { decision: "APPROVE" },
                        })
                      }
                      type="button"
                    >
                      <Check className="size-4" /> Chấp thuận
                    </button>
                    <button
                      className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-neutral-300 px-4 text-sm font-bold text-neutral-800"
                      onClick={() => setRejecting(item)}
                      type="button"
                    >
                      <X className="size-4" /> Yêu cầu điều chỉnh
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      )}

      {decision.error ? (
        <Feedback title="Chưa thể lưu quyết định" tone="error">
          Yêu cầu có thể đã được người khác xử lý. Hãy tải lại hàng chờ.
        </Feedback>
      ) : null}

      {rejecting ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4"
          role="presentation"
        >
          <form
            aria-labelledby="rejection-title"
            className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl"
            onSubmit={(event) => {
              event.preventDefault();
              decision.mutate({
                versionId: rejecting.id,
                input: { decision: "REJECT", reason: reason.trim() },
              });
            }}
          >
            <h2 className="text-xl font-bold" id="rejection-title">
              Nội dung cần người gửi điều chỉnh
            </h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              Viết cụ thể tài liệu hoặc thông tin còn thiếu. Nội dung này sẽ
              được hiển thị cho người gửi hồ sơ.
            </p>
            <textarea
              autoFocus
              className="mt-4 min-h-36 w-full rounded-xl border border-neutral-300 p-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
              maxLength={2000}
              minLength={20}
              onChange={(event) => setReason(event.target.value)}
              required
              value={reason}
            />
            <div className="mt-5 flex justify-end gap-2">
              <button
                className="min-h-11 rounded-xl px-4 text-sm font-bold text-neutral-700"
                onClick={() => {
                  setRejecting(null);
                  setReason("");
                }}
                type="button"
              >
                Hủy
              </button>
              <button
                className="min-h-11 rounded-xl bg-primary-700 px-4 text-sm font-bold text-white disabled:opacity-50"
                disabled={reason.trim().length < 20 || decision.isPending}
                type="submit"
              >
                Gửi yêu cầu điều chỉnh
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
