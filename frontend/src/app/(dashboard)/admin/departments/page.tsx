import { DepartmentWorkspace } from "@/components/hr/department-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function AdminDepartmentsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.departments.manage"]}>
      <DepartmentWorkspace />
    </RoleGate>
  );
}
