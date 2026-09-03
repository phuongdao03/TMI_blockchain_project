import { Landmark } from "lucide-react";

import { CouncilSessionList } from "@/components/council/council-session-list";
import { SelectControl } from "@/components/ui/form-controls";
import type { CouncilSessionStatus } from "@/lib/api/types";

const statuses: Array<[string, string]> = [
  ["", "Tất cả phiên"],
  ["DRAFT", "Đang chuẩn bị"],
  ["OPEN", "Đang xét duyệt"],
  ["CLOSED", "Đã kết thúc"],
];

export default async function CouncilPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; status?: string }>;
}) {
  const parameters = await searchParams;
  const page = Math.max(1, Number(parameters.page) || 1);
  const status = statuses.some(([value]) => value === parameters.status)
    ? (parameters.status as CouncilSessionStatus | undefined)
    : undefined;

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            <Landmark aria-hidden="true" className="size-4" />
            Quyết định hồ sơ
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Phiên xét duyệt
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            Tổ chức phiên xử lý cuối cùng cho các hồ sơ đã hoàn tất thẩm định.
            Nhân sự tham gia xem kết quả, chọn hướng xử lý và ghi rõ lý do.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border bg-neutral-200">
          <div className="bg-white px-5 py-3">
            <p className="text-xs font-semibold text-neutral-500">Mục đích</p>
            <p className="mt-1 font-bold">Thống nhất kết quả hồ sơ</p>
          </div>
          <div className="bg-white px-5 py-3">
            <p className="text-xs font-semibold text-neutral-500">Kết quả</p>
            <p className="mt-1 font-bold">Được lưu vào biên bản phiên</p>
          </div>
        </div>
      </header>
      <form className="flex flex-col gap-3 rounded-2xl border bg-white p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label
            className="text-xs font-bold uppercase tracking-wider text-neutral-500"
            htmlFor="council-status"
          >
            Trạng thái phiên
          </label>
          <SelectControl
            className="mt-2 min-h-11 w-full rounded-xl border bg-white px-3 text-sm font-semibold sm:max-w-xs"
            defaultValue={status ?? ""}
            id="council-status"
            name="status"
          >
            {statuses.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectControl>
        </div>
        <button
          className="min-h-11 rounded-xl bg-neutral-950 px-5 text-sm font-bold text-white hover:bg-neutral-800"
          type="submit"
        >
          Áp dụng bộ lọc
        </button>
      </form>
      <CouncilSessionList page={page} pageSize={10} status={status} />
    </div>
  );
}
