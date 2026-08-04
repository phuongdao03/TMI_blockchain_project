import {
  BadgeCheck,
  CircleAlert,
  Clock3,
  FilePenLine,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import type { DossierStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const labels: Record<DossierStatus, string> = {
  DRAFT: "Bản nháp",
  SUBMITTED: "Đã nộp",
  PRECHECK: "Đang tiền kiểm",
  NEEDS_SUPPLEMENT: "Cần bổ sung",
  UNDER_REVIEW: "Đang thẩm định",
  COUNCIL_REVIEW: "Hội đồng xem xét",
  APPROVED: "Đã phê duyệt",
  REJECTED: "Bị từ chối",
  PAYMENT_PENDING: "Chờ thanh toán",
  PAID: "Đã thanh toán",
  ANCHOR_PENDING: "Chờ neo blockchain",
  ANCHORED: "Đã neo blockchain",
  CERTIFICATE_ISSUED: "Đã phát hành chứng thư",
  PUBLISHED: "Đã công bố",
  REVOKED: "Đã thu hồi",
  CANCELLED: "Đã hủy",
};

const styles: Record<DossierStatus, string> = {
  DRAFT: "border-slate-200 bg-slate-100 text-slate-700",
  SUBMITTED: "border-blue-200 bg-blue-50 text-blue-800",
  PRECHECK: "border-sky-200 bg-sky-50 text-sky-800",
  NEEDS_SUPPLEMENT: "border-amber-200 bg-amber-50 text-amber-800",
  UNDER_REVIEW: "border-violet-200 bg-violet-50 text-violet-800",
  COUNCIL_REVIEW: "border-purple-200 bg-purple-50 text-purple-800",
  APPROVED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  REJECTED: "border-red-200 bg-red-50 text-red-800",
  PAYMENT_PENDING: "border-amber-200 bg-amber-50 text-amber-800",
  PAID: "border-emerald-200 bg-emerald-50 text-emerald-800",
  ANCHOR_PENDING: "border-cyan-200 bg-cyan-50 text-cyan-800",
  ANCHORED: "border-cyan-200 bg-cyan-50 text-cyan-800",
  CERTIFICATE_ISSUED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  PUBLISHED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  REVOKED: "border-red-200 bg-red-50 text-red-800",
  CANCELLED: "border-slate-300 bg-slate-100 text-slate-700",
};

function StatusIcon({ status }: { status: DossierStatus }) {
  if (status === "DRAFT") return <FilePenLine aria-hidden="true" />;
  if (status === "NEEDS_SUPPLEMENT") return <CircleAlert aria-hidden="true" />;
  if (status === "REJECTED" || status === "REVOKED") {
    return <XCircle aria-hidden="true" />;
  }
  if (
    [
      "APPROVED",
      "PAID",
      "ANCHORED",
      "CERTIFICATE_ISSUED",
      "PUBLISHED",
    ].includes(status)
  ) {
    return <BadgeCheck aria-hidden="true" />;
  }
  if (status === "SUBMITTED" || status.includes("REVIEW")) {
    return <Clock3 aria-hidden="true" />;
  }
  return <ShieldCheck aria-hidden="true" />;
}

export function DossierStatusBadge({
  className,
  status,
}: {
  className?: string;
  status: DossierStatus;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold",
        styles[status],
        className,
      )}
    >
      <span className="[&>svg]:size-3.5">
        <StatusIcon status={status} />
      </span>
      {labels[status]}
    </span>
  );
}

export function dossierStatusLabel(status: DossierStatus) {
  return labels[status];
}
