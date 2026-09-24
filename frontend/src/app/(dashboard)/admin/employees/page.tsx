import { RoleGate } from "@/components/auth/role-gate";
import { EmployeeWorkspace } from "@/components/hr/employee-workspace";

export default function AdminEmployeesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.employees.read"]}>
      <EmployeeWorkspace />
    </RoleGate>
  );
}
