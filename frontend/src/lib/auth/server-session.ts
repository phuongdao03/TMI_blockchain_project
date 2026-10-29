import { cookies } from "next/headers";
import { cache } from "react";

import type { AuthUser, SuccessEnvelope } from "@/lib/api/types";
import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";

export interface ServerAuthState {
  user: AuthUser | null;
  hasRefreshCookie: boolean;
  hasSessionCookie: boolean;
}

export const getServerAuthState = cache(async (): Promise<ServerAuthState> => {
  const cookieStore = await cookies();
  const hasRefreshCookie = Boolean(cookieStore.get("cns_refresh"));
  const hasSessionCookie =
    hasRefreshCookie || Boolean(cookieStore.get("cns_access"));
  if (!cookieStore.get("cns_access")) {
    return { user: null, hasRefreshCookie, hasSessionCookie };
  }
  const cookieHeader = cookieStore
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join("; ");
  const apiBaseUrl = resolveServerApiBaseUrl();

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
      signal: AbortSignal.timeout(4_000),
    });
    if (!response.ok) {
      return { user: null, hasRefreshCookie, hasSessionCookie };
    }
    const payload = (await response.json()) as SuccessEnvelope<AuthUser>;
    return { user: payload.data, hasRefreshCookie, hasSessionCookie };
  } catch {
    return { user: null, hasRefreshCookie, hasSessionCookie };
  }
});
