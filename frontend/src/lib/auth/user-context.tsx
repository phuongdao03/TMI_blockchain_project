"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { authApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import { SessionActivityMonitor } from "@/components/auth/session-activity-monitor";
import { LoginVoucher } from "@/components/vouchers/login-voucher";
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
      <AuthUserContext.Provider value={user}>
        {children}
      </AuthUserContext.Provider>
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
  const [sessionCheckRequested, setVerifySession] = useState(false);
  const verifySession =
    sessionCheckRequested || (!initialUser && hasSessionCookie);
  const [sessionSyncPending, setSessionSyncPending] = useState(false);
  const serverState = useRef({ initialUser, hasSessionCookie });

  useEffect(() => {
    const previous = serverState.current;
    if (
      previous.initialUser === initialUser &&
      previous.hasSessionCookie === hasSessionCookie
    )
      return;
    serverState.current = { initialUser, hasSessionCookie };
    // A router refresh is authoritative over a previously recovered identity.
    // Cancel its in-flight lookup so an old response cannot restore that user.
    void queryClient.cancelQueries({ queryKey: AUTH_ME_QUERY_KEY });
    if (initialUser || !hasSessionCookie) {
      queryClient.setQueryData(AUTH_ME_QUERY_KEY, initialUser);
    } else {
      void queryClient.invalidateQueries({ queryKey: AUTH_ME_QUERY_KEY });
    }
  }, [hasSessionCookie, initialUser, queryClient]);

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
      : verifySession &&
          (session.isPending || (session.isFetching && !session.data))
        ? "loading"
        : user
          ? "authenticated"
          : hasSessionCookie && !verifySession
            ? "loading"
            : "unauthenticated";

  return (
    <AuthStatusContext.Provider value={status}>
      <AuthUserContext.Provider value={user}>
        <SessionActivityMonitor enabled={Boolean(user)} />
        <LoginVoucher
          userId={status === "authenticated" ? (user?.id ?? null) : null}
          roles={user?.roles ?? []}
          isEmployee={user?.isEmployee}
        />
        {children}
      </AuthUserContext.Provider>
    </AuthStatusContext.Provider>
  );
}

export function useAuthUser() {
  return useContext(AuthUserContext);
}

export function useAuthStatus() {
  return useContext(AuthStatusContext);
}
