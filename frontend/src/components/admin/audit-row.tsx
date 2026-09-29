import { Clock3 } from "lucide-react";

import {
  actorLabel,
  auditEventSummary,
  auditOutcome,
  auditTargetLabel,
  formatAuditTimestamp,
  integrityLabels,
} from "@/components/admin/audit-presenters";
import type { AuditLogItem } from "@/lib/api/types";

function IntegrityBadge({ row }: { row: AuditLogItem }) {
  const outcome = auditOutcome(row);
  const integrity = integrityLabels[row.integrityStatus];
  return (
    <span
      className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-xs font-semibold ${outcome.className}`}
      title={`Tính toàn vẹn bản ghi: ${integrity.label}`}
    >
      {outcome.label}
    </span>
  );
}

export function AuditRow({ row }: { row: AuditLogItem }) {
  const timestamp = formatAuditTimestamp(row.createdAt);
  return (
    <tr className="audit-event-row border-t border-neutral-200 align-top transition-colors">
      <td className="whitespace-nowrap px-5 py-4 text-neutral-600">
        <span className="audit-event-title block font-semibold">
          {timestamp.time}
        </span>
        <span className="mt-1 block text-xs">{timestamp.date}</span>
      </td>
      <td className="px-5 py-4" data-testid="audit-row-summary">
        <span className="audit-event-title font-semibold">
          {auditEventSummary(row)}
        </span>
        <span className="mt-1 block text-xs text-neutral-500">
          {auditTargetLabel(row)}
        </span>
      </td>
      <td className="px-5 py-4 text-neutral-700">
        {actorLabel(row.actorType, row.actorService)}
      </td>
      <td className="px-5 py-4">
        <IntegrityBadge row={row} />
      </td>
    </tr>
  );
}

export function AuditCard({ row }: { row: AuditLogItem }) {
  const timestamp = formatAuditTimestamp(row.createdAt);
  return (
    <article
      className="audit-event-card rounded-2xl border p-4"
      data-testid="audit-mobile-row"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="rounded-xl bg-neutral-100 p-2 text-neutral-600">
          <Clock3 aria-hidden="true" className="size-4" />
        </span>
        <IntegrityBadge row={row} />
      </div>
      <h3 className="audit-event-title mt-4 text-base font-bold leading-6">
        {auditEventSummary(row)}
      </h3>
      <p className="mt-1 text-sm leading-6 text-neutral-600">
        {auditTargetLabel(row)} · {actorLabel(row.actorType, row.actorService)}
      </p>
      <time
        className="mt-3 block text-xs font-medium text-neutral-500"
        dateTime={row.createdAt}
      >
        {timestamp.time} · {timestamp.date}
      </time>
    </article>
  );
}
