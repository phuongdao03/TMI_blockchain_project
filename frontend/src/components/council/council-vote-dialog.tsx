"use client";

import { Check, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import type { CouncilVoteChoice } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const choices: Array<{
  value: CouncilVoteChoice;
  label: string;
  description: string;
}> = [
  {
    value: "APPROVE",
    label: "Phê duyệt",
    description: "Hồ sơ đáp ứng điều kiện xác lập.",
  },
  {
    value: "REJECT",
    label: "Từ chối",
    description: "Hồ sơ không đáp ứng điều kiện.",
  },
  {
    value: "REQUEST_MORE_INFO",
    label: "Yêu cầu bổ sung",
    description: "Cần thêm tài liệu hoặc làm rõ.",
  },
  {
    value: "ABSTAIN",
    label: "Không biểu quyết",
    description: "Tính vào quorum nhưng không tạo quyết định.",
  },
];

export function CouncilVoteDialog({
  isPending,
  onVote,
}: {
  isPending: boolean;
  onVote: (input: {
    choice: CouncilVoteChoice;
    reason: string;
  }) => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [choice, setChoice] = useState<CouncilVoteChoice | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reviewVote = () => {
    if (!choice) {
      setError("Vui lòng chọn phương án biểu quyết.");
      return;
    }
    if (!reason.trim()) {
      setError("Vui lòng nêu lý do cho phiếu biểu quyết.");
      return;
    }
    setError(null);
    setConfirmOpen(true);
  };

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)}>
        <Send aria-hidden="true" className="size-4" />
        Biểu quyết hồ sơ
      </Button>
    );
  }

  return (
    <>
      <section
        aria-labelledby="vote-form-title"
        className="rounded-2xl border border-primary-200 bg-primary-50/50 p-5"
      >
        <h3 className="text-lg font-bold" id="vote-form-title">
          Phiếu biểu quyết
        </h3>
        <p className="mt-1 text-sm text-neutral-600">
          Phiếu được khóa ngay sau khi gửi. Hãy kiểm tra kỹ lựa chọn và lý do.
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {choices.map((item) => (
            <button
              aria-label={item.label}
              aria-pressed={choice === item.value}
              className={cn(
                "min-h-20 rounded-xl border bg-white p-3 text-left transition focus-visible:outline-2 focus-visible:outline-primary-600",
                choice === item.value
                  ? "border-primary-500 ring-2 ring-primary-100"
                  : "border-neutral-200 hover:border-primary-300",
              )}
              key={item.value}
              onClick={() => setChoice(item.value)}
              type="button"
            >
              <span className="flex items-center justify-between gap-2 text-sm font-bold">
                {item.label}
                {choice === item.value ? (
                  <Check
                    aria-hidden="true"
                    className="size-4 text-primary-700"
                  />
                ) : null}
              </span>
              <span className="mt-1 block text-xs leading-5 text-neutral-500">
                {item.description}
              </span>
            </button>
          ))}
        </div>
        <label
          className="mt-4 block text-sm font-bold"
          htmlFor="council-vote-reason"
        >
          Lý do biểu quyết
        </label>
        <textarea
          aria-describedby={error ? "council-vote-error" : undefined}
          className="mt-2 min-h-28 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
          id="council-vote-reason"
          maxLength={2_000}
          onChange={(event) => setReason(event.target.value)}
          value={reason}
        />
        {error ? (
          <p
            className="mt-2 text-sm font-semibold text-red-700"
            id="council-vote-error"
            role="alert"
          >
            {error}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button onClick={() => setOpen(false)} variant="ghost">
            Hủy
          </Button>
          <Button disabled={isPending} onClick={reviewVote}>
            Kiểm tra phiếu biểu quyết
          </Button>
        </div>
      </section>
      <ConfirmationDialog
        confirmLabel="Xác nhận và gửi phiếu"
        description="Phiếu biểu quyết không thể chỉnh sửa hoặc gửi lại sau khi xác nhận."
        isPending={isPending}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          if (!choice) return;
          void onVote({ choice, reason: reason.trim() })
            .then(() => {
              setConfirmOpen(false);
              setOpen(false);
            })
            .catch(() => undefined);
        }}
        open={confirmOpen}
        title="Xác nhận phiếu biểu quyết"
      />
    </>
  );
}
