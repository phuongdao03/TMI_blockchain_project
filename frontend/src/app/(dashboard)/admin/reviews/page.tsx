import { RoleGate } from "@/components/auth/role-gate";
import { ReviewAssignmentQueue } from "@/components/admin/review-assignment-queue";

export default function AdminReviewsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["review.assign"]}>
      <ReviewAssignmentQueue />
    </RoleGate>
  );
}
