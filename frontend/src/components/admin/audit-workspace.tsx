"use client";

import { useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";

import { auditApi } from "@/lib/api/client";

export function AuditWorkspace() {
  const audit = useQuery({ queryKey: ["admin", "audit"], queryFn: () => auditApi.list() });
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header><p className="flex items-center gap-2 text-sm font-bold text-primary-700"><ScrollText className="size-4" />Kiểm soát thay đổi</p><h1 className="mt-2 text-3xl font-bold">Nhật ký audit</h1><p className="mt-2 text-sm text-neutral-600">Bản ghi chỉ đọc cho các thao tác quan trọng trong hệ thống.</p></header>
      <section className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white">
        {audit.isPending ? <p className="p-6" role="status">Đang tải nhật ký...</p> : null}
        <table className="min-w-full text-left text-sm"><thead className="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500"><tr><th className="px-5 py-3">Thời gian</th><th className="px-5 py-3">Hành động</th><th className="px-5 py-3">Tài nguyên</th><th className="px-5 py-3">Actor</th><th className="px-5 py-3">Request</th></tr></thead><tbody>{audit.data?.data.map((row) => <tr className="border-t border-neutral-100" key={row.id}><td className="whitespace-nowrap px-5 py-4">{new Date(row.createdAt).toLocaleString("vi-VN")}</td><td className="px-5 py-4 font-bold">{row.action}</td><td className="px-5 py-4"><span className="block">{row.resourceType}</span><span className="font-mono text-xs text-neutral-400">{row.resourceId}</span></td><td className="px-5 py-4 font-mono text-xs">{row.actorUserId ?? "SYSTEM"}</td><td className="px-5 py-4 font-mono text-xs">{row.requestId ?? "-"}</td></tr>)}</tbody></table>
        {audit.data?.data.length === 0 ? <p className="p-6 text-neutral-500">Chưa có bản ghi audit.</p> : null}
      </section>
    </div>
  );
}
