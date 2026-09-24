import { RoleGate } from "@/components/auth/role-gate";
import { LeaveWorkspace } from "@/components/hr/leave-workspace";

export default function LeavePage() {
  return (
    <RoleGate
      allowed={["USER", "MODERATOR", "SUPER_ADMIN"]}
      permissions={["hr.leave.self"]}
    >
      <LeaveWorkspace />
    </RoleGate>
  );
}
