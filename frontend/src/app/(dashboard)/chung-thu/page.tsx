import { BadgeCheck } from "lucide-react";

import { CertificateList } from "@/components/certificates/certificate-list";

export default async function CertificatesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = Math.max(1, Number(rawPage) || 1);
  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <header>
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          <BadgeCheck className="size-4" /> Kho chứng thư
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Chứng thư đã phát hành
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
          Quản lý bản PDF riêng tư và kiểm tra bằng chứng blockchain của tài
          sản.
        </p>
      </header>
      <CertificateList page={page} />
    </div>
  );
}
