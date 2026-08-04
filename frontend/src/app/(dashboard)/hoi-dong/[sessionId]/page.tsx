import { CouncilWorkspace } from "@/components/council/council-workspace";

export default async function CouncilDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <CouncilWorkspace sessionId={sessionId} />;
}
