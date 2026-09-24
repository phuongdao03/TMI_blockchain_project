import { RoleGate } from "@/components/auth/role-gate";
import { PayrollWorkspace } from "@/components/hr/payroll-workspace";

export default function AdminPayrollPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["hr.payroll.read"]}>
      <PayrollWorkspace />
    </RoleGate>
  );
}
