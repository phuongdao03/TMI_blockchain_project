import { RoleGate } from "@/components/auth/role-gate";
import { OvertimeWorkspace } from "@/components/hr/overtime-workspace";

export default function OvertimePage() {
  return (
    <RoleGate
      allowed={["USER", "MODERATOR", "SUPER_ADMIN"]}
      permissions={["hr.overtime.self"]}
    >
      <OvertimeWorkspace />
    </RoleGate>
  );
}
