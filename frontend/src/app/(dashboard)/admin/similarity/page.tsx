import { ArrowLeftRight } from "lucide-react";

import { SimilarityCaseQueue } from "@/components/admin/similarity-case-queue";
import { RoleGate } from "@/components/auth/role-gate";

export default function AdminSimilarityPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="mx-auto max-w-7xl space-y-7">
        <header className="border-b border-neutral-200 pb-7">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            <ArrowLeftRight aria-hidden="true" className="size-4" />
            Điều phối nghiệp vụ
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Phân công đối chiếu
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
            Giao các trường hợp cần xem xét cho chuyên gia phù hợp. Kết luận
            được lưu cùng căn cứ để phục vụ kiểm soát nội bộ.
          </p>
        </header>
        <SimilarityCaseQueue />
      </div>
    </RoleGate>
  );
}
