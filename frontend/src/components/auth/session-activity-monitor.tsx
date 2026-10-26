"use client";

import { useEffect } from "react";

import { authApi } from "@/lib/api/client";
import { broadcastAuthSessionChange } from "@/lib/auth/session-sync";
import {
  broadcastUserActivity,
  subscribeToUserActivity,
} from "@/lib/auth/session-activity-sync";

export const AUTH_IDLE_TIMEOUT_MS = 30 * 60 * 1_000;
const ACTIVITY_HEARTBEAT_INTERVAL_MS = 60 * 1_000;
const CROSS_TAB_BROADCAST_INTERVAL_MS = 5 * 1_000;

export function SessionActivityMonitor({
  enabled = true,
}: {
  enabled?: boolean;
}) {
  useEffect(() => {
    if (!enabled) return;

    let lastActivityAt = Date.now();
    let lastHeartbeatAt = 0;
    let lastBroadcastAt = 0;
    let idleTimer: ReturnType<typeof setTimeout>;
    let logoutStarted = false;

    const expireSession = () => {
      if (logoutStarted) return;
      logoutStarted = true;
      void authApi
        .logout()
        .catch(() => undefined)
        .finally(() => broadcastAuthSessionChange());
    };

    const scheduleIdleTimeout = () => {
      clearTimeout(idleTimer);
      const remaining = AUTH_IDLE_TIMEOUT_MS - (Date.now() - lastActivityAt);
      if (remaining <= 0) {
        expireSession();
        return;
      }
      idleTimer = setTimeout(expireSession, remaining);
    };

    const applyActivity = (timestamp: number, fromThisTab: boolean) => {
      if (logoutStarted) return;
      const now = Date.now();
      const safeTimestamp = Math.min(timestamp, now);
      if (safeTimestamp <= lastActivityAt) return;
      lastActivityAt = safeTimestamp;
      scheduleIdleTimeout();

      if (
        fromThisTab &&
        now - lastBroadcastAt >= CROSS_TAB_BROADCAST_INTERVAL_MS
      ) {
        lastBroadcastAt = now;
        broadcastUserActivity(safeTimestamp);
      }

      if (
        fromThisTab &&
        now - lastHeartbeatAt >= ACTIVITY_HEARTBEAT_INTERVAL_MS
      ) {
        lastHeartbeatAt = now;
        void authApi.recordActivity().catch((error: unknown) => {
          if (
            error instanceof Error &&
            "status" in error &&
            error.status === 401
          ) {
            expireSession();
            return;
          }
          if (lastHeartbeatAt === now) lastHeartbeatAt = 0;
        });
      }
    };

    const onUserActivity = () => applyActivity(Date.now(), true);
    const unsubscribe = subscribeToUserActivity((timestamp) =>
      applyActivity(timestamp, false),
    );
    const eventOptions: AddEventListenerOptions = {
      capture: true,
      passive: true,
    };
    window.addEventListener("pointerdown", onUserActivity, eventOptions);
    window.addEventListener("keydown", onUserActivity, eventOptions);
    window.addEventListener("touchstart", onUserActivity, eventOptions);
    window.addEventListener("scroll", onUserActivity, eventOptions);
    scheduleIdleTimeout();

    return () => {
      clearTimeout(idleTimer);
      unsubscribe();
      window.removeEventListener("pointerdown", onUserActivity, true);
      window.removeEventListener("keydown", onUserActivity, true);
      window.removeEventListener("touchstart", onUserActivity, true);
      window.removeEventListener("scroll", onUserActivity, true);
    };
  }, [enabled]);

  return null;
}
