"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { adminWithdrawalApi } from "@/lib/api/client";
import {
  bankVerificationStatusLabel,
  identityVerificationStatusLabel,
} from "@/lib/wallet-presentation";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

export function WithdrawalVerificationPanel({
  withdrawalId,
  userId,
  onComplete,
}: {
  withdrawalId: string;
  userId: string;
  onComplete: () => void;
}) {
  const client = useQueryClient();
  const [bankEvidence, setBankEvidence] = useState("");
  const [identityStatus, setIdentityStatus] = useState<
    "" | "VERIFIED" | "REJECTED"
  >("");
  const [identityEvidence, setIdentityEvidence] = useState("");
  const [identityReason, setIdentityReason] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const refresh = async () => {
    await client.invalidateQueries({
      queryKey: ["admin", "withdrawals", withdrawalId],
    });
    onComplete();
  };
  const verifyBank = useMutation({
    mutationFn: () =>
      adminWithdrawalApi.verifyBank(withdrawalId, bankEvidence.trim()),
    onSuccess: async (account) => {
      setMessage(
        `Trạng thái xác minh ngân hàng: ${bankVerificationStatusLabel(account.verificationStatus)}.`,
      );
      setError(false);
      setBankEvidence("");
      await refresh();
    },
    onError: () => {
      setMessage("");
      setError(true);
    },
  });
  const reviewIdentity = useMutation({
    mutationFn: () =>
      adminWithdrawalApi.reviewIdentity(userId, {
        status: identityStatus as "VERIFIED" | "REJECTED",
        evidenceReference: identityEvidence.trim(),
        reason: identityReason.trim(),
      }),
    onSuccess: async (result) => {
      setMessage(
        `Kết quả xác minh danh tính: ${identityVerificationStatusLabel(result.status)}.`,
      );
      setError(false);
      setIdentityStatus("");
      setIdentityEvidence("");
      setIdentityReason("");
      await refresh();
    },
    onError: () => {
      setMessage("");
      setError(true);
    },
  });

  return (
    <section
      aria-labelledby="verification-review-title"
      className="space-y-4 border-t border-[var(--theme-border)] pt-4"
    >
      <div>
        <h3 id="verification-review-title" className="font-bold">
          Xác minh trước khi phê duyệt
        </h3>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">
          Ghi nhận tham chiếu bằng chứng theo hồ sơ nội bộ; không nhập dữ liệu
          giấy tờ nhạy cảm vào đây.
        </p>
      </div>
      <form
        className="grid gap-3 rounded-lg border border-[var(--theme-border)] p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          verifyBank.mutate();
        }}
      >
        <label className="grid gap-1 text-sm font-semibold">
          Tham chiếu xác minh tài khoản ngân hàng
          <input
            className={inputClass}
            maxLength={512}
            minLength={10}
            onChange={(event) => setBankEvidence(event.target.value)}
            required
            value={bankEvidence}
          />
        </label>
        <Button
          className="min-h-11"
          disabled={verifyBank.isPending}
          type="submit"
          variant="outline"
        >
          {verifyBank.isPending ? "Đang xác minh…" : "Xác nhận ngân hàng"}
        </Button>
      </form>
      <form
        className="grid gap-3 rounded-lg border border-[var(--theme-border)] p-3 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (identityStatus) reviewIdentity.mutate();
        }}
      >
        <label className="grid gap-1 text-sm font-semibold">
          Kết quả xác minh danh tính
          <select
            className={inputClass}
            onChange={(event) =>
              setIdentityStatus(event.target.value as typeof identityStatus)
            }
            required
            value={identityStatus}
          >
            <option value="">Chọn kết quả</option>
            <option value="VERIFIED">Đã xác minh</option>
            <option value="REJECTED">Từ chối</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Tham chiếu bằng chứng
          <input
            className={inputClass}
            maxLength={128}
            minLength={5}
            onChange={(event) => setIdentityEvidence(event.target.value)}
            required
            value={identityEvidence}
          />
        </label>
        <label className="grid gap-1 text-sm font-semibold sm:col-span-2">
          Lý do và ghi chú kiểm tra
          <textarea
            className="min-h-20 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-sm"
            maxLength={1000}
            minLength={10}
            onChange={(event) => setIdentityReason(event.target.value)}
            required
            value={identityReason}
          />
        </label>
        <Button
          className="min-h-11 sm:justify-self-start"
          disabled={reviewIdentity.isPending || !identityStatus}
          type="submit"
        >
          {reviewIdentity.isPending ? "Đang lưu…" : "Lưu kết quả xác minh"}
        </Button>
      </form>
      {message ? (
        <p role="status" className="text-sm font-semibold text-emerald-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-red-700">
          Không lưu được kết quả xác minh. Hãy kiểm tra quyền và tham chiếu bằng
          chứng.
        </p>
      ) : null}
    </section>
  );
}
