import { RoleGate } from "@/components/auth/role-gate";
import { AttendanceWorkspace } from "@/components/hr/attendance-workspace";

export default function AttendancePage() {
  return (
    <RoleGate
      allowed={["USER", "MODERATOR", "SUPER_ADMIN"]}
      permissions={["hr.attendance.self"]}
    >
      <AttendanceWorkspace />
    </RoleGate>
  );
}
