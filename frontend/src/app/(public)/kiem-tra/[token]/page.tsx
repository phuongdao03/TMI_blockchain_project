import { permanentRedirect } from "next/navigation";

export default async function LegacyVerificationPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  permanentRedirect(`/verify/${encodeURIComponent(token)}`);
}
