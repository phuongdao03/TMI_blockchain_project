import { RoleGate } from "@/components/auth/role-gate";
import { ReviewAssignmentQueue } from "@/components/admin/review-assignment-queue";

const statuses = new Set(["SUBMITTED", "PRECHECK", "UNDER_REVIEW"]);

export default async function AdminReviewsPage({
  searchParams,
}: PageProps<"/admin/reviews">) {
  const { status } = await searchParams;
  const initialStatus =
    typeof status === "string" && statuses.has(status)
      ? (status as "SUBMITTED" | "PRECHECK" | "UNDER_REVIEW")
      : undefined;
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["review.assign"]}>
      <ReviewAssignmentQueue initialStatus={initialStatus} />
    </RoleGate>
  );
}
