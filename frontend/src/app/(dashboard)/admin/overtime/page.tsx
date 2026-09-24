import { RoleGate } from "@/components/auth/role-gate";
import { AdminOvertimeWorkspace } from "@/components/hr/admin-overtime-workspace";

export default function AdminOvertimePage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.overtime.read"]}>
      <AdminOvertimeWorkspace />
    </RoleGate>
  );
}
