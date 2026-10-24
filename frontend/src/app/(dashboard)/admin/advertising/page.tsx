import { RoleGate } from "@/components/auth/role-gate";
import { AdvertisingAdminWorkspace } from "@/components/advertising/advertising-admin-workspace";

export default function AdminAdvertisingPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <AdvertisingAdminWorkspace />
    </RoleGate>
  );
}
