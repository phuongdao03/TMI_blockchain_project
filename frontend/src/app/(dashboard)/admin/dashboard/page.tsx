import { OperationsDashboard } from "@/components/admin/operations-dashboard";
import { RoleGate } from "@/components/auth/role-gate";

export default function AdminDashboardPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <OperationsDashboard />
    </RoleGate>
  );
}
