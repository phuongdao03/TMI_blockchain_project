import type { ReactNode } from "react";

import { PublicExperienceShell } from "@/components/layout/public-experience-shell";
import { getServerAuthState } from "@/lib/auth/server-session";

export default async function PublicLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = await getServerAuthState();
  return <PublicExperienceShell user={user}>{children}</PublicExperienceShell>;
}
