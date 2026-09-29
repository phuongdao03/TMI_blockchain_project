import { RoleGate } from "@/components/auth/role-gate";
import { PeopleWorkspace } from "@/components/hr/people-workspace";

export default function AdminEmployeesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.employees.read"]}>
      <PeopleWorkspace />
    </RoleGate>
  );
}
