import { CmsWorkspace } from "@/components/admin/cms-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function CmsAdminPage() {
  return <RoleGate allowed={["CONTENT_ADMIN", "SUPER_ADMIN"]}><CmsWorkspace /></RoleGate>;
}
