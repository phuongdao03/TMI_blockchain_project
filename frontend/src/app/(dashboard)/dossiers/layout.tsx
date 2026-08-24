import type { ReactNode } from "react";

import { RoleGate } from "@/components/auth/role-gate";

export default function DossierLayout({ children }: { children: ReactNode }) {
  return <RoleGate allowed={["USER"]}>{children}</RoleGate>;
}
