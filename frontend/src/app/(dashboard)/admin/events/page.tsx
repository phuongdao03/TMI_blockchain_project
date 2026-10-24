import { AdminEventsWorkspace } from "@/components/events/admin-events-workspace";
import { RoleGate } from "@/components/auth/role-gate";

export default function AdminEventsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["memberships.manage"]}>
      <AdminEventsWorkspace />
    </RoleGate>
  );
}
