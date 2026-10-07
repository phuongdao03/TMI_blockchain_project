import Link from "next/link";

import { CertificateCorrectionList } from "@/components/admin/certificate-correction-list";
import { RoleGate } from "@/components/auth/role-gate";

export default function CertificateCorrectionsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <main className="mx-auto max-w-5xl space-y-6 pb-8">
        <header className="border-b border-neutral-200 pb-6">
          <Link
            className="text-sm font-bold text-primary-700 underline"
            href="/admin/certificates"
          >
            Quản lý bằng xác lập
          </Link>
          <h1 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">
            Sửa bằng xác lập đã cấp
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
            Tìm bằng đang có hiệu lực và phát hành bản điều chỉnh trong một lần
            xác nhận của quản trị viên. Phiên bản cũ được giữ để đối chiếu.
          </p>
        </header>
        <CertificateCorrectionList />
      </main>
    </RoleGate>
  );
}
