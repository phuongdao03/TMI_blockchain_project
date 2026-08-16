"use client";

import { usePathname } from "next/navigation";
import type { PropsWithChildren } from "react";

import { DashboardShell, PublicShell } from "@/components/layout/shells";
import type { AuthUser } from "@/lib/api/types";
import { AuthUserProvider } from "@/lib/auth/user-context";

const workspacePublicPaths = ["/search", "/works", "/map", "/verify"];

export function isWorkspacePublicPath(pathname: string): boolean {
  return workspacePublicPaths.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function PublicExperienceShell({
  children,
  user,
}: PropsWithChildren<{ user: AuthUser | null }>) {
  const pathname = usePathname() ?? "/";

  if (user && isWorkspacePublicPath(pathname)) {
    return (
      <AuthUserProvider user={user}>
        <DashboardShell>{children}</DashboardShell>
      </AuthUserProvider>
    );
  }

  return <PublicShell user={user}>{children}</PublicShell>;
}
