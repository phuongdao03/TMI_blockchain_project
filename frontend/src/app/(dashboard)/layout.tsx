import { Suspense, type ReactNode } from "react";
import { redirect } from "next/navigation";

import { DashboardAuthGuard } from "@/components/auth/dashboard-auth-guard";
import { DashboardShell } from "@/components/layout/shells";
import { PageLoading } from "@/components/ui/page-loading";
import { getServerAuthState } from "@/lib/auth/server-session";

async function DashboardLayoutContent({ children }: { children: ReactNode }) {
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

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<PageLoading />}>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </Suspense>
  );
}
