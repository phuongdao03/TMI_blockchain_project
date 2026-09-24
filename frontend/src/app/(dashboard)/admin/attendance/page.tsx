import { RoleGate } from "@/components/auth/role-gate";
import { AdminAttendanceWorkspace } from "@/components/hr/admin-attendance-workspace";

export default function AdminAttendancePage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.attendance.read"]}>
      <AdminAttendanceWorkspace />
    </RoleGate>
  );
}
