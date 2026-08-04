import { AuditWorkspace } from "@/components/admin/audit-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function AuditPage() {
  return <RoleGate allowed={["SUPER_ADMIN"]}><AuditWorkspace /></RoleGate>;
}
