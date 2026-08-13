import type { ReactNode } from "react";

import { RoleGate } from "@/components/auth/role-gate";

export default function CouncilLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGate allowed={["COUNCIL_MEMBER", "COUNCIL_SECRETARY", "SUPER_ADMIN"]}>
      {children}
    </RoleGate>
  );
}
