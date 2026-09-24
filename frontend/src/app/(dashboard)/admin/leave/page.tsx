import { RoleGate } from "@/components/auth/role-gate";
import { AdminLeaveWorkspace } from "@/components/hr/admin-leave-workspace";

export default function AdminLeavePage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.leave.read"]}>
      <AdminLeaveWorkspace />
    </RoleGate>
  );
}
