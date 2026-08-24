import type { PropsWithChildren } from "react";

import { PublicShell } from "@/components/layout/shells";
import type { AuthUser } from "@/lib/api/types";

export function PublicExperienceShell({
  children,
  user,
}: PropsWithChildren<{ user: AuthUser | null }>) {
  return <PublicShell user={user}>{children}</PublicShell>;
}
