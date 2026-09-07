"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck, Inbox, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ReviewLifecyclePanel } from "@/components/admin/review-lifecycle-panel";
import { EvidenceViewer } from "@/components/reviews/evidence-viewer";
import { adminReviewApi } from "@/lib/api/client";
import type {
  AdminReviewDossierDetail,
  AdminReviewDossierStatus,
} from "@/lib/api/types";

const statusLabels: Record<AdminReviewDossierStatus, string> = {
  SUBMITTED: "Chờ sơ kiểm",
  PRECHECK: "Đang sơ kiểm",
  UNDER_REVIEW: "Kiểm duyệt và quyết định",
};

function dossierStatusLabel(
  dossier:
    | AdminReviewDossierDetail
    | { status: AdminReviewDossierStatus; assignmentCount: number },
) {
  if (dossier.status !== "UNDER_REVIEW") return statusLabels[dossier.status];
  return dossier.assignmentCount > 0
    ? "Đang kiểm duyệt / chờ quyết định"
    : "Chờ phân công";
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
            ← Quản lý kiểm duyệt
          </Link>
          <h1 className="mt-3 text-3xl font-bold">{dossier.dossierTitle}</h1>
          <p className="mt-2 text-sm text-neutral-500">
            {dossier.dossierCode} · Phiên bản {dossier.versionNo} ·{" "}
            {dossierStatusLabel(dossier)}
          </p>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-2 text-xs font-bold text-amber-800">
          {dossier.assignmentCount} phân công
        </span>
      </header>
      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
        <h2 className="text-xl font-bold">Tài liệu trong hồ sơ</h2>
        <div className="mt-5">
          <EvidenceViewer
            documentRules={rules}
            evidences={dossier.snapshotJson.evidences}
          />
        </div>
      </section>
      <ReviewLifecyclePanel dossier={dossier} />
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
        <h1 className="mt-3 text-4xl font-bold">Kiểm duyệt hồ sơ</h1>
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
                    {dossierStatusLabel(dossier)}
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
