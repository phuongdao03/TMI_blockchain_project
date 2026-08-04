import { ReviewWorkspace } from "@/components/reviews/review-workspace";

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ assignmentId: string }>;
}) {
  const { assignmentId } = await params;
  return <ReviewWorkspace assignmentId={assignmentId} />;
}
