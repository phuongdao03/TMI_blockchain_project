"use client";

import { createContext, type ReactNode, useContext } from "react";

import type { AuthUser } from "@/lib/api/types";

const AuthUserContext = createContext<AuthUser | null>(null);

export function AuthUserProvider({
  children,
  user,
}: {
  children: ReactNode;
  user: AuthUser;
}) {
  return (
    <AuthUserContext.Provider value={user}>{children}</AuthUserContext.Provider>
  );
}

export function useAuthUser() {
  return useContext(AuthUserContext);
}
