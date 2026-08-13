import type { ReactNode } from "react";

import { PublicShell } from "@/components/layout/shells";
import { getServerAuthState } from "@/lib/auth/server-session";

export default async function PublicLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = await getServerAuthState();
  return <PublicShell user={user}>{children}</PublicShell>;
}
