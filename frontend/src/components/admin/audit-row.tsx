import type { AuditLogItem } from "@/lib/api/types";
import {
  actionLabel,
  actorLabel,
  integrityLabels,
  resourceLabel,
} from "@/components/admin/audit-presenters";

export function AuditRow({ row }: { row: AuditLogItem }) {
  const integrity = integrityLabels[row.integrityStatus];
  return (
    <tr className="border-t border-neutral-200 align-top">
      <td className="whitespace-nowrap px-5 py-4 text-neutral-600">
        {new Date(row.createdAt).toLocaleString("vi-VN")}
      </td>
      <td className="px-5 py-4">
        <span className="font-semibold text-ink-950">
          {actionLabel(row.action)}
        </span>
        <span className="mt-1 block text-xs text-neutral-500">
          {resourceLabel(row.resourceType)}
        </span>
      </td>
      <td className="px-5 py-4 text-neutral-700">
        {actorLabel(row.actorType)}
      </td>
      <td className="px-5 py-4">
        <span
          className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${integrity.className}`}
        >
          {integrity.label}
        </span>
      </td>
      <td className="px-5 py-4">
        <details className="group text-xs text-neutral-600">
          <summary className="cursor-pointer font-semibold text-primary-700 focus-visible:outline-2 focus-visible:outline-offset-2">
            Xem chi tiết
          </summary>
          <dl className="mt-3 grid gap-2">
            <div>
              <dt className="text-neutral-500">Đối tượng tham chiếu</dt>
              <dd className="break-all font-mono">{row.resourceId}</dd>
            </div>
            <div>
              <dt className="text-neutral-500">Mã yêu cầu</dt>
              <dd className="break-all font-mono">{row.requestId ?? "—"}</dd>
            </div>
          </dl>
        </details>
      </td>
    </tr>
  );
}
