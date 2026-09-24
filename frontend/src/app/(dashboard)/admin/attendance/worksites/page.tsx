import { RoleGate } from "@/components/auth/role-gate";
import { AttendanceConfigurationWorkspace } from "@/components/hr/attendance-configuration-workspace";

export default function AttendanceWorksitesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <AttendanceConfigurationWorkspace />
    </RoleGate>
  );
}
