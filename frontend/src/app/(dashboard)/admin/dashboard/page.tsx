import { OperationsDashboard } from "@/components/admin/operations-dashboard";
import { RoleGate } from "@/components/auth/role-gate";
import { HrDashboardSummary } from "@/components/hr/hr-dashboard-summary";

export default function AdminDashboardPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="space-y-8 pb-12">
        <HrDashboardSummary />
        <OperationsDashboard />
      </div>
    </RoleGate>
  );
}
