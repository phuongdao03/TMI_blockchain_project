import { CertificateDetail } from "@/components/certificates/certificate-detail";

export default async function CertificatePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return <CertificateDetail id={(await params).id} />;
}
