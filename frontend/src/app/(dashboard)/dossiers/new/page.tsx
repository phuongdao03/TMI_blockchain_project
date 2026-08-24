import { ArrowLeft, FilePlus2 } from "lucide-react";
import Link from "next/link";

import { DossierCreateForm } from "@/components/dossiers/dossier-create-form";
import { RoleGate } from "@/components/auth/role-gate";

export default function CreateDossierPage() {
  return (
    <RoleGate allowed={["USER"]}>
      <div className="mx-auto max-w-4xl space-y-7">
        <div>
          <Link
            className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-500 hover:text-primary-700"
            href="/dossiers"
          >
            <ArrowLeft aria-hidden="true" className="size-4" />
            Danh sách hồ sơ
          </Link>
          <p className="mt-4 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            <FilePlus2 aria-hidden="true" className="size-4" />
            Hồ sơ mới
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Khởi tạo hồ sơ xác lập
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            Bắt đầu với thông tin cốt lõi. Bạn có thể tiếp tục bổ sung bằng
            chứng và chỉnh sửa trước khi nộp.
          </p>
        </div>
        <DossierCreateForm />
      </div>
    </RoleGate>
  );
}
