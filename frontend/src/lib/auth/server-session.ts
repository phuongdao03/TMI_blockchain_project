import { cookies } from "next/headers";

import type { AuthUser, SuccessEnvelope } from "@/lib/api/types";
import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";

export interface ServerAuthState {
  user: AuthUser | null;
  hasRefreshCookie: boolean;
}

export async function getServerAuthState(): Promise<ServerAuthState> {
  const cookieStore = await cookies();
  const hasRefreshCookie = Boolean(cookieStore.get("tmi_refresh"));
  if (!cookieStore.get("tmi_access")) {
    return { user: null, hasRefreshCookie };
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
    });
    if (!response.ok) {
      return { user: null, hasRefreshCookie };
    }
    const payload = (await response.json()) as SuccessEnvelope<AuthUser>;
    return { user: payload.data, hasRefreshCookie };
  } catch {
    return { user: null, hasRefreshCookie };
  }
}
