import { VerificationPanel } from "@/components/public/verification-panel";
import { getServerAuthState } from "@/lib/auth/server-session";

export default async function VerifyPage() {
  const { user } = await getServerAuthState();
  const embedded = Boolean(user);
  return (
    <div
      className={
        embedded
          ? "mx-auto max-w-6xl rounded-2xl bg-[#151515] px-5 py-7 text-white shadow-[0_24px_70px_rgba(15,23,42,.12)] sm:px-7 lg:px-9"
          : "mx-auto min-h-[calc(100dvh-5rem)] max-w-6xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20"
      }
    >
      <VerificationPanel embedded={embedded} />
    </div>
  );
}
