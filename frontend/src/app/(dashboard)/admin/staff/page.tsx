import { RoleGate } from "@/components/auth/role-gate";
import { StaffAccountWorkspace } from "@/components/admin/staff-account-workspace";

export default function StaffAccountsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <StaffAccountWorkspace />
    </RoleGate>
  );
}
