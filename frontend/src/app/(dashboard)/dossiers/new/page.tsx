import { ArrowLeft, FilePlus2 } from "lucide-react";
import Link from "next/link";

import { DossierCreateForm } from "@/components/dossiers/dossier-create-form";
import { ApplicantEntryGate } from "@/components/dossiers/applicant-entry-gate";

export default function CreateDossierPage() {
  return (
    <ApplicantEntryGate>
      <div className="mx-auto max-w-4xl space-y-7">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-neutral-500 hover:text-primary-700"
              href="/dossiers"
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
              Danh sách hồ sơ
            </Link>
            <p className="hidden items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700 sm:inline-flex">
              <FilePlus2 aria-hidden="true" className="size-4" />
              Hồ sơ mới
            </p>
          </div>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Chuẩn bị hồ sơ đề cử
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            Chọn biểu mẫu và điền thông tin để tạo bản nháp. Sau đó bạn sẽ bổ
            sung tài liệu và gửi hồ sơ để được xem xét.
          </p>
        </div>
        <DossierCreateForm />
      </div>
    </ApplicantEntryGate>
  );
}
