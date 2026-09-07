import { RoleGate } from "@/components/auth/role-gate";
import { ReviewAssignmentQueue } from "@/components/admin/review-assignment-queue";

export default async function AdminReviewDossierPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = await params;
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["review.assign"]}>
      <ReviewAssignmentQueue initialDossierId={dossierId} />
    </RoleGate>
  );
}
