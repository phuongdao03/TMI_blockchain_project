import { RoleGate } from "@/components/auth/role-gate";
import { ModeratorHrDashboardSummary } from "@/components/hr/moderator-hr-dashboard-summary";
import { MyWorkAllocationList } from "@/components/work-allocations/my-work-allocation-list";

export default function MyWorkAllocationsPage() {
  return (
    <RoleGate allowed={["MODERATOR"]}>
      <div className="mx-auto max-w-7xl space-y-8 pb-12">
        <MyWorkAllocationList />
        <ModeratorHrDashboardSummary />
      </div>
    </RoleGate>
  );
}
