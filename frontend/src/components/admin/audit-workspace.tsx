"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ScrollText,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useMemo, useState } from "react";

import { AuditRow } from "@/components/admin/audit-row";
import { Button, buttonVariants } from "@/components/ui/button";
import { auditApi } from "@/lib/api/client";
import type { AuditListFilters } from "@/lib/api/types";

const inputClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-ink-950 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100";

export function AuditWorkspace() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");

  const filters: AuditListFilters = {
    page,
    pageSize: 20,
    action: action || undefined,
    resourceType: resourceType || undefined,
    createdFrom: createdFrom ? `${createdFrom}T00:00:00.000Z` : undefined,
    createdTo: createdTo ? `${createdTo}T23:59:59.999Z` : undefined,
  };
  const audit = useQuery({
    queryKey: ["admin", "audit", filters],
    queryFn: () => auditApi.list(filters),
  });
  const integrity = useMutation({
    mutationFn: () => auditApi.checkIntegrity(10_000),
  });
  const exportHref = useMemo(() => {
    const parameters = new URLSearchParams({ limit: "10000" });
    if (action) parameters.set("action", action);
    if (resourceType) parameters.set("resourceType", resourceType);
    if (createdFrom)
      parameters.set("createdFrom", `${createdFrom}T00:00:00.000Z`);
    if (createdTo) parameters.set("createdTo", `${createdTo}T23:59:59.999Z`);
    return `/api/v1/admin/audit/exports.csv?${parameters.toString()}`;
  }, [action, resourceType, createdFrom, createdTo]);
  const exceptions = integrity.data
    ? integrity.data.counts.TAMPERED + integrity.data.counts.KEY_UNAVAILABLE
    : null;
  const incompleteIntegrityScan = integrity.data?.isComplete === false;
  const totalPages = Math.max(1, Math.ceil((audit.data?.meta.total ?? 0) / 20));

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <header className="grid overflow-hidden border border-ink-900 bg-ink-950 text-white lg:grid-cols-[1fr_22rem]">
        <div className="p-7 sm:p-9">
          <p className="flex items-center gap-2 text-xs font-bold tracking-[0.18em] text-gold-300 uppercase">
            <ScrollText aria-hidden="true" className="size-4" />
            Kiểm soát thay đổi
          </p>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Lịch sử vận hành
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
            Theo dõi các quyết định và thay đổi quan trọng. Thông tin kỹ thuật
            được thu gọn để danh sách tập trung vào việc đã xảy ra và trạng thái
            kiểm chứng.
          </p>
          <a
            className={`${buttonVariants({ variant: "outline" })} mt-6 inline-flex`}
            download
            href={exportHref}
          >
            <Download aria-hidden="true" className="size-4" />
            Tải báo cáo CSV
          </a>
        </div>
        <aside className="border-t border-white/10 bg-white/[0.04] p-7 lg:border-t-0 lg:border-l">
          <ShieldCheck className="size-6 text-gold-300" />
          <h2 className="mt-4 text-lg font-bold">Tính toàn vẹn bản ghi</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Đối chiếu các bản ghi trong phạm vi an toàn và báo riêng những mục
            cần kiểm tra.
          </p>
          <Button
            className="mt-5 w-full"
            disabled={integrity.isPending}
            onClick={() => integrity.mutate()}
          >
            {integrity.isPending ? "Đang kiểm tra…" : "Kiểm tra ngay"}
          </Button>
          {integrity.data ? (
            <p
              className={`mt-4 flex items-center gap-2 text-sm font-semibold ${exceptions || incompleteIntegrityScan ? "text-amber-200" : "text-emerald-200"}`}
              role="status"
            >
              {exceptions || incompleteIntegrityScan ? (
                <TriangleAlert className="size-4" />
              ) : null}
              {incompleteIntegrityScan
                ? `Phạm vi kiểm tra chưa đầy đủ (${integrity.data.scanned}/${integrity.data.total} bản ghi)`
                : exceptions
                  ? `${exceptions} bản ghi cần xử lý`
                  : "Không phát hiện bất thường"}
            </p>
          ) : null}
          {integrity.isError ? (
            <p className="mt-4 text-sm text-red-200" role="alert">
              Chưa thể hoàn tất kiểm tra. Vui lòng thử lại.
            </p>
          ) : null}
        </aside>
      </header>

      <section
        aria-label="Bộ lọc lịch sử"
        className="grid gap-4 border border-neutral-200 bg-white p-5 md:grid-cols-2 xl:grid-cols-4"
      >
        <label className="text-sm font-semibold" htmlFor="audit-action">
          Loại hoạt động
          <select
            className={inputClass}
            id="audit-action"
            name="action"
            onChange={(event) => {
              setAction(event.target.value);
              setPage(1);
            }}
            value={action}
          >
            <option value="">Tất cả hoạt động</option>
            <option value="dossier.approved">Hồ sơ được phê duyệt</option>
            <option value="certificate.version.approved">
              Cập nhật chứng thư được duyệt
            </option>
            <option value="certificate.version.rejected">
              Cập nhật chứng thư bị từ chối
            </option>
            <option value="audit.exported">Báo cáo được tải</option>
            <option value="audit.integrity_checked">
              Tính toàn vẹn được kiểm tra
            </option>
          </select>
        </label>
        <label className="text-sm font-semibold" htmlFor="audit-resource-type">
          Nhóm nội dung
          <select
            className={inputClass}
            id="audit-resource-type"
            name="resourceType"
            onChange={(event) => {
              setResourceType(event.target.value);
              setPage(1);
            }}
            value={resourceType}
          >
            <option value="">Tất cả</option>
            <option value="dossier">Hồ sơ</option>
            <option value="certificate">Chứng thư</option>
            <option value="document">Tài liệu</option>
            <option value="payment">Thanh toán</option>
          </select>
        </label>
        <label className="text-sm font-semibold" htmlFor="audit-created-from">
          Từ ngày
          <input
            className={inputClass}
            id="audit-created-from"
            max={createdTo || undefined}
            name="createdFrom"
            onChange={(event) => {
              setCreatedFrom(event.target.value);
              setPage(1);
            }}
            type="date"
            value={createdFrom}
          />
        </label>
        <label className="text-sm font-semibold" htmlFor="audit-created-to">
          Đến ngày
          <input
            className={inputClass}
            id="audit-created-to"
            min={createdFrom || undefined}
            name="createdTo"
            onChange={(event) => {
              setCreatedTo(event.target.value);
              setPage(1);
            }}
            type="date"
            value={createdTo}
          />
        </label>
      </section>

      <section className="overflow-hidden border border-neutral-200 bg-white">
        <div className="flex items-center justify-between gap-4 border-b border-neutral-200 px-5 py-4">
          <div>
            <h2 className="font-bold text-ink-950">Hoạt động gần đây</h2>
            <p className="mt-1 text-xs text-neutral-500">
              {audit.data?.meta.total ?? 0} thay đổi phù hợp
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Button
              aria-label="Trang trước"
              disabled={page === 1}
              onClick={() => setPage((current) => current - 1)}
              variant="outline"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span aria-live="polite">
              {page}/{totalPages}
            </span>
            <Button
              aria-label="Trang sau"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
              variant="outline"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
        {audit.isPending ? (
          <p className="p-6 text-sm text-neutral-600" role="status">
            Đang tải lịch sử vận hành…
          </p>
        ) : null}
        {audit.isError ? (
          <p className="p-6 text-sm text-red-700" role="alert">
            Không thể tải lịch sử lúc này. Vui lòng thử lại.
          </p>
        ) : null}
        {audit.data?.data.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-neutral-50 text-xs tracking-wide text-neutral-500 uppercase">
                <tr>
                  <th className="px-5 py-3">Thời gian</th>
                  <th className="px-5 py-3">Hoạt động</th>
                  <th className="px-5 py-3">Thực hiện bởi</th>
                  <th className="px-5 py-3">Trạng thái</th>
                  <th className="px-5 py-3">Thông tin</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.data.map((row) => (
                  <AuditRow key={row.id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {audit.data?.data.length === 0 ? (
          <p className="p-8 text-center text-sm text-neutral-500">
            Chưa có thay đổi phù hợp với bộ lọc.
          </p>
        ) : null}
      </section>
    </main>
  );
}
