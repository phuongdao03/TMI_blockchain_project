import { RoleGate } from "@/components/auth/role-gate";
import { WorkAllocationWorkspace } from "@/components/work-allocations/work-allocation-workspace";

export default function WorkAllocationsPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <WorkAllocationWorkspace />
    </RoleGate>
  );
}
