import type { ReactNode } from "react";
import { redirect } from "next/navigation";

import { DashboardAuthGuard } from "@/components/auth/dashboard-auth-guard";
import { DashboardShell } from "@/components/layout/shells";
import { getServerAuthState } from "@/lib/auth/server-session";

export default async function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  const authState = await getServerAuthState();
  if (!authState.user && !authState.hasRefreshCookie) {
    redirect("/login?next=/dashboard");
  }
  return (
    <DashboardAuthGuard initialUser={authState.user}>
      <DashboardShell>{children}</DashboardShell>
    </DashboardAuthGuard>
  );
}
