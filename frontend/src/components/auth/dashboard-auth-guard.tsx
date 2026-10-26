"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { subscribeToAuthSessionChanges } from "@/lib/auth/session-sync";

import { authApi } from "@/lib/api/client";
import { safeLocalDestination } from "@/lib/auth/safe-destination";
import type { AuthUser } from "@/lib/api/types";
import { AuthUserProvider } from "@/lib/auth/user-context";
import { SessionActivityMonitor } from "@/components/auth/session-activity-monitor";

export function DashboardAuthGuard({
  children,
  initialUser,
}: {
  children: ReactNode;
  initialUser: AuthUser | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [sessionSyncPending, setSessionSyncPending] = useState(false);
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const {
    data: user,
    isPending,
    isFetching,
    isError,
  } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.currentUser,
    initialData: initialUser ?? undefined,
    retry: false,
    staleTime: 60_000,
  });
  const effectiveUser = isError ? null : user;

  useEffect(
    () =>
      subscribeToAuthSessionChanges(() => {
        setSessionSyncPending(true);
        queryClient.removeQueries({
          predicate: (query) => query.queryKey[0] !== "auth",
        });
        void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      }),
    [queryClient],
  );

  useEffect(() => {
    if (!isPending && !isFetching && !effectiveUser) {
      const next = safeLocalDestination(
        `${pathname || "/workspace"}${query ? `?${query}` : ""}`,
        "/workspace",
      );
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [effectiveUser, isPending, isFetching, pathname, query, router]);

  if (isPending || !effectiveUser || (sessionSyncPending && isFetching)) {
    return (
      <div
        className="grid min-h-dvh place-items-center bg-background text-neutral-700"
        role="status"
      >
        <span className="flex items-center gap-3">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          Đang xác thực phiên…
        </span>
      </div>
    );
  }
  return (
    <AuthUserProvider user={effectiveUser}>
      <SessionActivityMonitor />
      {children}
    </AuthUserProvider>
  );
}
