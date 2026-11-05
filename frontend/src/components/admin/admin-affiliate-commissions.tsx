"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { adminAffiliateApi } from "@/lib/api/client";
import type { AdminAffiliateCommission } from "@/lib/api/types";
import {
  affiliateServiceLabel,
  basisPointsAsPercent,
  commissionStatusLabel,
} from "@/lib/affiliate-presentation";
import { formatVnd } from "@/lib/wallet/summary";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

type ReviewAction = "reject" | "reverse";

export function AdminAffiliateCommissions() {
  const client = useQueryClient();
  const [status, setStatus] = useState("");
  const [affiliateUserId, setAffiliateUserId] = useState("");
  const [review, setReview] = useState<{ id: string; action: ReviewAction } | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState(false);
  const commissions = useQuery({
    queryKey: ["admin", "affiliate", "commissions", status, affiliateUserId],
    queryFn: () => adminAffiliateApi.commissions({ status: status || undefined, affiliateUserId: affiliateUserId.trim() || undefined }),
  });
  const refresh = () => client.invalidateQueries({ queryKey: ["admin", "affiliate", "commissions"] });
  const approve = useMutation({
    mutationFn: adminAffiliateApi.approveCommission,
    onSuccess: async () => { setError(false); await refresh(); },
    onError: () => setError(true),
  });
  const reviewMutation = useMutation({
    mutationFn: ({ id, action, reason }: { id: string; action: ReviewAction; reason: string }) =>
      action === "reject"
        ? adminAffiliateApi.rejectCommission(id, reason)
        : adminAffiliateApi.reverseCommission(id, reason),
    onSuccess: async () => { setError(false); setReview(null); setReason(""); await refresh(); },
    onError: () => setError(true),
  });

  const submitReview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!review || reason.trim().length < 10) return;
    setError(false);
    reviewMutation.mutate({ id: review.id, action: review.action, reason: reason.trim() });
  };

  const rowActions = (commission: AdminAffiliateCommission) => (
    <div className="flex flex-wrap gap-2">
      {commission.status === "PENDING" ? (
        <Button className="min-h-10" disabled={approve.isPending} onClick={() => approve.mutate(commission.id)} type="button">Phê duyệt</Button>
      ) : null}
      {commission.status === "PENDING" ? (
        <Button className="min-h-10" onClick={() => { setReview({ id: commission.id, action: "reject" }); setReason(""); }} type="button" variant="outline">Từ chối</Button>
      ) : null}
      {["PENDING", "ON_HOLD", "AVAILABLE"].includes(commission.status) ? (
        <Button className="min-h-10" onClick={() => { setReview({ id: commission.id, action: "reverse" }); setReason(""); }} type="button" variant="outline">Thu hồi</Button>
      ) : null}
    </div>
  );

  return (
    <section aria-labelledby="affiliate-commissions-title" className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
      <div>
        <h2 id="affiliate-commissions-title" className="text-lg font-bold sm:text-xl">Duyệt hoa hồng</h2>
        <p className="mt-1 text-sm text-[var(--theme-muted)]">Phê duyệt khoản hợp lệ hoặc ghi rõ lý do khi từ chối hay thu hồi.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm font-semibold">
          Trạng thái hoa hồng
          <select className={inputClass} onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="">Tất cả trạng thái</option>
            {(["PENDING", "ON_HOLD", "AVAILABLE", "REJECTED", "REVERSED", "SUPPRESSED"] as const).map((value) => <option key={value} value={value}>{commissionStatusLabel(value)}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Mã người giới thiệu
          <input className={inputClass} onChange={(event) => setAffiliateUserId(event.target.value)} placeholder="Không bắt buộc" value={affiliateUserId} />
        </label>
      </div>
      {commissions.isPending ? <p aria-busy="true" className="py-5 text-sm" role="status">Đang tải danh sách hoa hồng…</p> : null}
      {commissions.isError ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4" role="alert">
          <p className="text-sm text-red-700">Chưa tải được danh sách hoa hồng. Vui lòng thử lại.</p>
          <Button className="min-h-10" onClick={() => void commissions.refetch()} type="button" variant="outline">Tải lại</Button>
        </div>
      ) : null}
      {commissions.data?.length ? (
        <div className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)]">
          {commissions.data.map((commission) => (
            <article className="space-y-3 p-4" key={commission.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold">{affiliateServiceLabel(commission.serviceCode)} · {formatVnd(commission.commissionAmountMinor)}</p>
                  <p className="mt-1 text-xs text-[var(--theme-muted)]">Trạng thái: {commissionStatusLabel(commission.status)}</p>
                  <p className="mt-1 break-all font-mono text-xs text-[var(--theme-muted)]">Mã người giới thiệu: {commission.affiliateUserId} · Mã người được giới thiệu: {commission.referredUserId}</p>
                  <p className="mt-1 text-xs text-[var(--theme-muted)]">Ghi nhận {new Date(commission.earnedAt).toLocaleDateString("vi-VN")} · hết thời gian chờ {new Date(commission.holdUntil).toLocaleDateString("vi-VN")} · tỷ lệ {basisPointsAsPercent(commission.rateBasisPoints)}</p>
                  {commission.reviewReason || commission.reversalReason ? <p className="mt-1 text-sm">Lý do: {commission.reviewReason ?? commission.reversalReason}</p> : null}
                </div>
                {rowActions(commission)}
              </div>
              {review?.id === commission.id ? (
                <form className="grid gap-2 border-t border-[var(--theme-border)] pt-3 sm:grid-cols-[minmax(0,1fr)_auto]" onSubmit={submitReview}>
                  <label className="grid gap-1 text-sm font-semibold">
                    {review.action === "reject" ? "Lý do từ chối" : "Lý do thu hồi"} (ít nhất 10 ký tự)
                    <input className={inputClass} maxLength={1000} minLength={10} onChange={(event) => setReason(event.target.value)} required value={reason} />
                  </label>
                  <Button className="min-h-11 self-end" disabled={reviewMutation.isPending || reason.trim().length < 10} type="submit">
                    {reviewMutation.isPending ? "Đang lưu…" : review.action === "reject" ? "Xác nhận từ chối" : "Xác nhận thu hồi"}
                  </Button>
                </form>
              ) : null}
            </article>
          ))}
        </div>
      ) : commissions.data ? <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">Không có khoản hoa hồng phù hợp với bộ lọc này.</p> : null}
      {error ? <p role="alert" className="text-sm text-red-700">Không cập nhật được khoản hoa hồng. Hãy kiểm tra trạng thái khoản và quyền thao tác.</p> : null}
    </section>
  );
}
