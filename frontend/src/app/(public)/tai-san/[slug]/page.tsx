import { permanentRedirect } from "next/navigation";

export default async function LegacyPublicWorkPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  permanentRedirect(`/works/${encodeURIComponent(slug)}`);
}
