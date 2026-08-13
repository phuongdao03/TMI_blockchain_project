import { FilePlus2, FolderKanban } from "lucide-react";
import Link from "next/link";

import { DossierList } from "@/components/dossiers/dossier-list";
import type { DossierStatus } from "@/lib/api/types";

const statusOptions: Array<[string, string]> = [
  ["", "Tất cả trạng thái"],
  ["DRAFT", "Bản nháp"],
  ["SUBMITTED", "Đã nộp"],
  ["NEEDS_SUPPLEMENT", "Cần bổ sung"],
  ["UNDER_REVIEW", "Đang thẩm định"],
  ["APPROVED", "Đã phê duyệt"],
];

export default async function DossiersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; status?: string }>;
}) {
  const parameters = await searchParams;
  const page = Math.max(1, Number(parameters.page) || 1);
  const status = statusOptions.some(([value]) => value === parameters.status)
    ? (parameters.status as DossierStatus | undefined)
    : undefined;

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            <FolderKanban aria-hidden="true" className="size-4" />
            Không gian hồ sơ
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Hồ sơ xác lập
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            Chuẩn bị thông tin, quản lý bằng chứng và theo dõi từng phiên bản
            trong một quy trình minh bạch.
          </p>
        </div>
        <Link
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary-600 px-5 text-sm font-bold text-white shadow-lg shadow-primary-950/15 hover:bg-primary-700"
          href="/dossiers/new"
        >
          <FilePlus2 aria-hidden="true" className="size-4" />
          Tạo hồ sơ mới
        </Link>
      </div>

      <form className="flex flex-col gap-3 rounded-2xl border border-neutral-200 bg-white p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label
            className="text-xs font-bold uppercase tracking-wider text-neutral-500"
            htmlFor="status-filter"
          >
            Trạng thái
          </label>
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm font-semibold sm:max-w-xs"
            defaultValue={status ?? ""}
            id="status-filter"
            name="status"
          >
            {statusOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button
          className="min-h-11 rounded-xl border border-neutral-200 bg-neutral-950 px-5 text-sm font-bold text-white hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng bộ lọc
        </button>
      </form>

      <DossierList page={page} pageSize={10} status={status} />
    </div>
  );
}
