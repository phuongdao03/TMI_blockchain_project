import { Suspense, type ReactNode } from "react";

import { PublicExperienceShell } from "@/components/layout/public-experience-shell";
import { PageLoading } from "@/components/ui/page-loading";
import { getServerAuthState } from "@/lib/auth/server-session";

async function PublicLayoutContent({ children }: { children: ReactNode }) {
  const authState = await getServerAuthState();
  return (
    <PublicExperienceShell
      hasSessionCookie={authState.hasSessionCookie}
      user={authState.user}
    >
      {children}
    </PublicExperienceShell>
  );
}

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<PageLoading />}>
      <PublicLayoutContent>{children}</PublicLayoutContent>
    </Suspense>
  );
}
