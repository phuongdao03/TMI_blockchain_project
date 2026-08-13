import { FileClock } from "lucide-react";

import { CertificateVersionQueue } from "@/components/admin/certificate-version-queue";
import { RoleGate } from "@/components/auth/role-gate";

export default function CertificateUpdatesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="mx-auto max-w-7xl space-y-7">
        <header className="border-b border-neutral-200 pb-7">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            <FileClock className="size-4" /> Việc cần xem xét
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Cập nhật chứng thư
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
            Xem lý do thay đổi, đối chiếu phiên bản hồ sơ đã được phê duyệt và
            theo dõi tiến trình phát hành bản mới.
          </p>
        </header>
        <CertificateVersionQueue />
      </div>
    </RoleGate>
  );
}
