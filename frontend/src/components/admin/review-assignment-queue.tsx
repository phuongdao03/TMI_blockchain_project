"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck, Inbox, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EvidenceViewer } from "@/components/reviews/evidence-viewer";
import { adminReviewApi, staffAccountsApi } from "@/lib/api/client";
import type {
  AdminReviewDossierDetail,
  AdminReviewDossierStatus,
} from "@/lib/api/types";

const statusLabels: Record<AdminReviewDossierStatus, string> = {
  SUBMITTED: "Chờ sơ kiểm",
  PRECHECK: "Đang sơ kiểm",
  UNDER_REVIEW: "Chờ phân công",
};

function DossierActions({ dossier }: { dossier: AdminReviewDossierDetail }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [reason, setReason] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const reviewers = useQuery({
    queryKey: ["staff-accounts", "active-reviewers"],
    queryFn: () =>
      staffAccountsApi.list({
        role: "MODERATOR",
        status: "ACTIVE",
        pageSize: 100,
      }),
    enabled: dossier.status === "UNDER_REVIEW",
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin-review-dossiers"] }),
      queryClient.invalidateQueries({
        queryKey: ["admin-review-dossier", dossier.dossierId],
      }),
    ]);
  };
  const transition = useMutation({
    mutationFn: (action: "start" | "pass" | "supplement") => {
      if (action === "start")
        return adminReviewApi.startPrecheck(dossier.dossierId, reason);
      if (action === "pass")
        return adminReviewApi.passPrecheck(dossier.dossierId, reason);
      return adminReviewApi.requestSupplement(dossier.dossierId, reason);
    },
    onSuccess: async (_, action) => {
      if (action === "supplement") router.push("/admin/reviews");
      await refresh();
    },
  });
  const assign = useMutation({
    mutationFn: () =>
      adminReviewApi.assign(
        dossier.dossierId,
        [reviewerId],
        dueAt ? new Date(dueAt).toISOString() : undefined,
      ),
    onSuccess: refresh,
  });
  const busy = transition.isPending || assign.isPending;

  return (
    <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
      <h3 className="text-lg font-bold">Xử lý hồ sơ</h3>
      {dossier.status === "UNDER_REVIEW" ? (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold">
            Nhân viên thẩm định
            <select
              className="mt-2 min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
              onChange={(event) => setReviewerId(event.target.value)}
              value={reviewerId}
            >
              <option value="">Chọn nhân viên</option>
              {reviewers.data?.data.map((reviewer) => (
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
          <button
            className="min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:opacity-50 md:col-span-2"
            disabled={!reviewerId || busy}
            onClick={() => assign.mutate()}
            type="button"
          >
            {assign.isPending ? "Đang phân công…" : "Phân công thẩm định"}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <label className="block text-sm font-semibold">
            Ghi chú xử lý
            <textarea
              className="mt-2 min-h-24 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3"
              onChange={(event) => setReason(event.target.value)}
              placeholder="Nhập lý do hoặc kết quả kiểm tra"
              value={reason}
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              className="min-h-11 rounded-xl bg-primary-700 px-5 font-bold text-white disabled:opacity-50"
              disabled={!reason.trim() || busy}
              onClick={() =>
                transition.mutate(
                  dossier.status === "SUBMITTED" ? "start" : "pass",
                )
              }
              type="button"
            >
              {dossier.status === "SUBMITTED"
                ? "Bắt đầu sơ kiểm"
                : "Đạt sơ kiểm"}
            </button>
            {dossier.status === "PRECHECK" ? (
              <button
                className="min-h-11 rounded-xl border border-red-300 px-5 font-bold text-red-700 disabled:opacity-50"
                disabled={!reason.trim() || busy}
                onClick={() => transition.mutate("supplement")}
                type="button"
              >
                Yêu cầu bổ sung
              </button>
            ) : null}
          </div>
        </div>
      )}
      {transition.isError || assign.isError ? (
        <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
          Chưa thể cập nhật hồ sơ. Vui lòng kiểm tra dữ liệu và thử lại.
        </p>
      ) : null}
      {assign.isSuccess ? (
        <p className="mt-4 text-sm font-semibold text-green-700" role="status">
          Đã giao hồ sơ cho nhân viên thẩm định.
        </p>
      ) : null}
    </section>
  );
}

function DossierDetail({ dossierId }: { dossierId: string }) {
  const detail = useQuery({
    queryKey: ["admin-review-dossier", dossierId],
    queryFn: () => adminReviewApi.get(dossierId),
  });
  if (detail.isPending)
    return (
      <div className="grid min-h-56 place-items-center" role="status">
        <LoaderCircle className="size-7 animate-spin" />
        <span className="sr-only">Đang tải hồ sơ</span>
      </div>
    );
  if (detail.isError) return <p role="alert">Không thể mở hồ sơ này.</p>;

  const dossier = detail.data;
  const rules = dossier.snapshotJson.dossier.dossierType?.documentRules ?? [];
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            className="text-sm font-semibold text-primary-700"
            href="/admin/reviews"
          >
            ← Hàng chờ phân công
          </Link>
          <h1 className="mt-3 text-3xl font-bold">{dossier.dossierTitle}</h1>
          <p className="mt-2 text-sm text-neutral-500">
            {dossier.dossierCode} · Phiên bản {dossier.versionNo} ·{" "}
            {statusLabels[dossier.status]}
          </p>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-2 text-xs font-bold text-amber-800">
          {dossier.assignmentCount} phân công
        </span>
      </header>
      <DossierActions dossier={dossier} />
      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
        <h2 className="text-xl font-bold">Tài liệu trong hồ sơ</h2>
        <div className="mt-5">
          <EvidenceViewer
            documentRules={rules}
            evidences={dossier.snapshotJson.evidences}
          />
        </div>
      </section>
    </div>
  );
}

export function ReviewAssignmentQueue({
  initialDossierId,
}: {
  initialDossierId?: string;
}) {
  const [status, setStatus] = useState<AdminReviewDossierStatus | "">("");
  const dossiers = useQuery({
    queryKey: ["admin-review-dossiers", status],
    queryFn: () =>
      adminReviewApi.list({ status: status || undefined, pageSize: 50 }),
    enabled: !initialDossierId,
  });
  if (initialDossierId) return <DossierDetail dossierId={initialDossierId} />;

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header>
        <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          Điều phối hồ sơ
        </p>
        <h1 className="mt-3 text-4xl font-bold">Phân công thẩm định</h1>
        <p className="mt-3 text-neutral-600">
          Sơ kiểm hồ sơ đã nộp, xem tài liệu và giao việc cho nhân viên thẩm
          định.
        </p>
      </header>
      <label className="block max-w-sm text-sm font-bold">
        Trạng thái
        <select
          className="mt-2 min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
          onChange={(event) =>
            setStatus(event.target.value as AdminReviewDossierStatus | "")
          }
          value={status}
        >
          <option value="">Tất cả hồ sơ chờ xử lý</option>
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {dossiers.isPending ? (
        <div className="grid min-h-56 place-items-center" role="status">
          <LoaderCircle className="size-7 animate-spin" />
          <span className="sr-only">Đang tải hàng chờ</span>
        </div>
      ) : dossiers.isError ? (
        <p
          className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-800"
          role="alert"
        >
          Chưa thể tải hàng chờ phân công.
        </p>
      ) : dossiers.data.data.length === 0 ? (
        <div className="rounded-2xl border border-dashed p-12 text-center">
          <Inbox className="mx-auto size-9 text-neutral-400" />
          <h2 className="mt-4 text-xl font-bold">Không có hồ sơ chờ xử lý</h2>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
          {dossiers.data.data.map((dossier) => (
            <article
              className="flex flex-wrap items-center justify-between gap-5 border-b border-[var(--theme-border)] p-5 last:border-0"
              key={dossier.dossierId}
            >
              <div className="flex min-w-0 gap-4">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-800">
                  <ClipboardCheck className="size-5" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide text-primary-700">
                    {statusLabels[dossier.status]}
                  </p>
                  <h2 className="mt-1 truncate text-lg font-bold">
                    {dossier.dossierTitle}
                  </h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    {dossier.dossierCode} · {dossier.assignmentCount} phân công
                  </p>
                </div>
              </div>
              <Link
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[var(--theme-border)] px-4 font-bold"
                href={`/admin/reviews/${dossier.dossierId}`}
              >
                Xem và xử lý <ArrowRight className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
