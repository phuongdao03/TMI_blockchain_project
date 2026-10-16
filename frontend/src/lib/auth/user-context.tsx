"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import { authApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import { subscribeToAuthSessionChanges } from "@/lib/auth/session-sync";

const AuthUserContext = createContext<AuthUser | null>(null);
const AuthStatusContext = createContext<AuthStatus>("unauthenticated");

export type AuthStatus =
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "error";

const AUTH_ME_QUERY_KEY = ["auth", "me"] as const;

export function AuthUserProvider({
  children,
  user,
}: {
  children: ReactNode;
  user: AuthUser;
}) {
  return (
    <AuthStatusContext.Provider value="authenticated">
      <AuthUserContext.Provider value={user}>{children}</AuthUserContext.Provider>
    </AuthStatusContext.Provider>
  );
}

export function PublicAuthProvider({
  children,
  initialUser,
  hasSessionCookie,
}: {
  children: ReactNode;
  initialUser: AuthUser | null;
  hasSessionCookie: boolean;
}) {
  const queryClient = useQueryClient();
  const [verifySession, setVerifySession] = useState(
    !initialUser && hasSessionCookie,
  );
  const [sessionSyncPending, setSessionSyncPending] = useState(false);

  useEffect(() => {
    const verify = () => {
      setSessionSyncPending(true);
      setVerifySession(true);
      void queryClient.invalidateQueries({ queryKey: AUTH_ME_QUERY_KEY });
    };
    const unsubscribe = subscribeToAuthSessionChanges(verify);
    window.addEventListener("focus", verify);
    return () => {
      unsubscribe();
      window.removeEventListener("focus", verify);
    };
  }, [queryClient]);

  const session = useQuery({
    queryKey: AUTH_ME_QUERY_KEY,
    queryFn: authApi.currentUser,
    enabled: verifySession,
    initialData: initialUser ?? undefined,
    retry: false,
    staleTime: 30_000,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });

  const user = session.isError
    ? null
    : verifySession
      ? (session.data ?? null)
      : initialUser;
  const status: AuthStatus = session.isError
    ? "error"
    : sessionSyncPending && session.isFetching
      ? "loading"
      : session.isPending || (session.isFetching && !session.data)
        ? "loading"
        : user
          ? "authenticated"
          : hasSessionCookie && !verifySession
            ? "loading"
            : "unauthenticated";

  return (
    <AuthStatusContext.Provider value={status}>
      <AuthUserContext.Provider value={user}>{children}</AuthUserContext.Provider>
    </AuthStatusContext.Provider>
  );
}

export function useAuthUser() {
  return useContext(AuthUserContext);
}

export function useAuthStatus() {
  return useContext(AuthStatusContext);
}
