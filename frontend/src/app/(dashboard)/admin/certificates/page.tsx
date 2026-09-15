import { RoleGate } from "@/components/auth/role-gate";
import { AdminCertificateManager } from "@/components/admin/admin-certificate-manager";

export default function AdminCertificatesPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <AdminCertificateManager />
    </RoleGate>
  );
}
