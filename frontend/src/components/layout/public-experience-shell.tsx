import type { PropsWithChildren } from "react";

import { PublicShell } from "@/components/layout/shells";
import type { AuthUser } from "@/lib/api/types";
import { PublicAuthProvider } from "@/lib/auth/user-context";

export function PublicExperienceShell({
  children,
  user,
  hasSessionCookie = Boolean(user),
}: PropsWithChildren<{
  user: AuthUser | null;
  hasSessionCookie?: boolean;
}>) {
  return (
    <PublicAuthProvider
      initialUser={user}
      hasSessionCookie={hasSessionCookie}
    >
      <PublicShell>{children}</PublicShell>
    </PublicAuthProvider>
  );
}
