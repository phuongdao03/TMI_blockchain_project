import { FilePlus2, FolderKanban } from "lucide-react";
import Link from "next/link";

import { DossierList } from "@/components/dossiers/dossier-list";
import { SelectControl } from "@/components/ui/form-controls";
import type { DossierStatus } from "@/lib/api/types";

const statusGroups: Array<{
  label: string;
  options: Array<[DossierStatus, string]>;
}> = [
  {
    label: "Cần bạn xử lý",
    options: [
      ["DRAFT", "Bản nháp"],
      ["NEEDS_SUPPLEMENT", "Cần bổ sung"],
      ["PAYMENT_PENDING", "Chờ thanh toán"],
    ],
  },
  {
    label: "Đang xử lý",
    options: [
      ["SUBMITTED", "Đã nộp"],
      ["PRECHECK", "Đang kiểm tra"],
      ["UNDER_REVIEW", "Đang thẩm định"],
      ["COUNCIL_REVIEW", "Chờ quyết định"],
      ["APPROVED", "Đã duyệt · Chờ quyết định phí"],
      ["PAID", "Đã xác nhận phí"],
      ["ANCHOR_PENDING", "Đang xác lập"],
      ["ANCHORED", "Đang chuẩn bị bằng"],
    ],
  },
  {
    label: "Đã hoàn tất",
    options: [
      ["CERTIFICATE_ISSUED", "Đã cấp bằng"],
      ["PUBLISHED", "Đã công bố"],
    ],
  },
  {
    label: "Đã kết thúc",
    options: [
      ["REJECTED", "Không được duyệt"],
      ["REVOKED", "Đã thu hồi"],
      ["CANCELLED", "Đã hủy"],
    ],
  },
];

export default async function DossiersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; status?: string }>;
}) {
  const parameters = await searchParams;
  const page = Math.max(1, Number(parameters.page) || 1);
  const status = statusGroups.some((group) =>
    group.options.some(([value]) => value === parameters.status),
  )
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
          <SelectControl
            className="mt-2 min-h-11 w-full rounded-xl border border-neutral-200 bg-white px-3 text-sm font-semibold sm:max-w-xs"
            defaultValue={status ?? ""}
            id="status-filter"
            name="status"
          >
            <option value="">Tất cả trạng thái</option>
            {statusGroups.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.options.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </optgroup>
            ))}
          </SelectControl>
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
