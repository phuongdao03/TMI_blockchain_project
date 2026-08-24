import type { Metadata } from "next";

import { VerificationPanel } from "@/components/public/verification-panel";
import { getServerAuthState } from "@/lib/auth/server-session";

export const metadata: Metadata = {
  title: "Xác minh chứng thư",
  robots: { index: false, follow: false },
};

export default async function VerifyTokenPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { user } = await getServerAuthState();
  const embedded = Boolean(user);
  return (
    <div
      className={
        embedded
          ? "public-theme-surface public-theme-surface--embedded mx-auto max-w-6xl rounded-2xl px-5 py-7 shadow-[0_24px_70px_rgba(15,23,42,.12)] sm:px-7 lg:px-9"
          : "public-theme-surface mx-auto min-h-[calc(100dvh-5rem)] max-w-6xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20"
      }
    >
      <VerificationPanel embedded={embedded} token={(await params).token} />
    </div>
  );
}
