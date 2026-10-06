import Link from "next/link";

import { CertificateContentCorrection } from "@/components/admin/certificate-content-correction";
import { RoleGate } from "@/components/auth/role-gate";

export default async function CertificateCorrectionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <main className="mx-auto max-w-6xl space-y-6 pb-8">
        <header className="border-b border-neutral-200 pb-6">
          <Link className="text-sm font-bold text-primary-700 underline" href="/admin/certificates/corrections">Bằng đã cấp</Link>
          <h1 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">Chỉnh nội dung bằng xác lập</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
            Xem lại nội dung trước khi gửi duyệt. Quản trị viên khác sẽ quyết định việc cấp phiên bản mới.
          </p>
        </header>
        <CertificateContentCorrection certificateId={id} key={id} />
      </main>
    </RoleGate>
  );
}
