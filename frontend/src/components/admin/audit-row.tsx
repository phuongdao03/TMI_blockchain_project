import { Clock3 } from "lucide-react";

import {
  actorLabel,
  auditEventSummary,
  formatAuditTimestamp,
  integrityLabels,
  resourceLabel,
} from "@/components/admin/audit-presenters";
import type { AuditLogItem } from "@/lib/api/types";

function IntegrityBadge({ row }: { row: AuditLogItem }) {
  const integrity = integrityLabels[row.integrityStatus];
  return (
    <span
      className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-xs font-semibold ${integrity.className}`}
    >
      {integrity.label}
    </span>
  );
}

function TechnicalDetails({ row }: { row: AuditLogItem }) {
  return (
    <details className="group text-xs text-neutral-600">
      <summary className="cursor-pointer font-semibold text-primary-700 focus-visible:outline-2 focus-visible:outline-offset-2">
        Thông tin kỹ thuật
      </summary>
      <dl className="mt-3 grid max-w-sm gap-2 rounded-lg bg-neutral-50 p-3">
        <div>
          <dt className="text-neutral-500">Loại sự kiện</dt>
          <dd className="break-all font-mono">{row.action}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Mã đối tượng</dt>
          <dd className="break-all font-mono">{row.resourceId}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Mã yêu cầu</dt>
          <dd className="break-all font-mono">{row.requestId ?? "—"}</dd>
        </div>
      </dl>
    </details>
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
          {resourceLabel(row.resourceType)}
        </span>
        <span className="mt-1 block text-xs text-neutral-500">
          {actorLabel(row.actorType, row.actorService)}
        </span>
      </td>
      <td className="px-5 py-4 text-neutral-700">
        {actorLabel(row.actorType, row.actorService)}
      </td>
      <td className="px-5 py-4">
        <IntegrityBadge row={row} />
      </td>
      <td className="px-5 py-4" data-testid="audit-row-technical-details">
        <TechnicalDetails row={row} />
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
        {resourceLabel(row.resourceType)} ·{" "}
        {actorLabel(row.actorType, row.actorService)}
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
