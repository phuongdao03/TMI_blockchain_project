import type { Metadata } from "next";

import { VerificationPanel } from "@/components/public/verification-panel";
import { getServerAuthState } from "@/lib/auth/server-session";
import { isCertificateNumber } from "@/lib/verification/certificate-route";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<Metadata> {
  const identifier = decodeURIComponent((await params).token);
  const certificateNumber = isCertificateNumber(identifier);
  return {
    title: certificateNumber ? `Chứng thư ${identifier}` : "Xác minh chứng thư",
    description:
      "Kiểm tra chứng thư xác lập tài sản số và bằng chứng ghi nhận trên Polygon.",
    alternates: certificateNumber
      ? { canonical: `/verify/${encodeURIComponent(identifier)}` }
      : undefined,
    openGraph: certificateNumber
      ? {
          title: `Chứng thư xác lập tài sản số ${identifier}`,
          description:
            "Đối chiếu dấu vân tay số và bằng chứng blockchain của Tinh Hoa Việt.",
          type: "website",
          url: `/verify/${encodeURIComponent(identifier)}`,
        }
      : undefined,
    robots: certificateNumber
      ? { index: true, follow: true }
      : { index: false, follow: false },
  };
}

export default async function VerifyTokenPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { user } = await getServerAuthState();
  const identifier = decodeURIComponent((await params).token);
  const certificateNumber = isCertificateNumber(identifier);
  const embedded = Boolean(user);
  return (
    <div
      className={
        embedded
          ? "public-theme-surface public-theme-surface--embedded mx-auto max-w-6xl rounded-2xl px-5 py-7 shadow-[0_24px_70px_rgba(15,23,42,.12)] sm:px-7 lg:px-9"
          : "public-theme-surface mx-auto min-h-[calc(100dvh-5rem)] max-w-6xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20"
      }
    >
      <VerificationPanel
        embedded={embedded}
        initialLookup={certificateNumber ? identifier : ""}
        token={certificateNumber ? undefined : identifier}
      />
    </div>
  );
}
