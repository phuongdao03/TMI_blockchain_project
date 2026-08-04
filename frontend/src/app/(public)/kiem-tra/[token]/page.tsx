import { VerificationPanel } from "@/components/public/verification-panel";

export default async function VerifyTokenPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  return (
    <div className="mx-auto min-h-[calc(100dvh-5rem)] max-w-6xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
      <VerificationPanel token={(await params).token} />
    </div>
  );
}
