import type { ReactNode } from "react";

import { RoleGate } from "@/components/auth/role-gate";

export default function ReviewsLayout({ children }: { children: ReactNode }) {
  return <RoleGate allowed={["REVIEWER", "SUPER_ADMIN"]}>{children}</RoleGate>;
}
