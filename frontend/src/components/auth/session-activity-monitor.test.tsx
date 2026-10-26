import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  SessionActivityMonitor,
  AUTH_IDLE_TIMEOUT_MS,
} from "./session-activity-monitor";

const authApi = vi.hoisted(() => ({
  logout: vi.fn().mockResolvedValue({ status: "logged_out" }),
  recordActivity: vi.fn().mockResolvedValue({ status: "active" }),
}));
const broadcastAuthSessionChange = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({ authApi }));
vi.mock("@/lib/auth/session-sync", () => ({ broadcastAuthSessionChange }));

describe("SessionActivityMonitor", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-26T00:00:00Z"));
    authApi.logout.mockClear();
    authApi.recordActivity.mockClear();
    broadcastAuthSessionChange.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("ends a session after 30 minutes without user activity", async () => {
    render(<SessionActivityMonitor />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTH_IDLE_TIMEOUT_MS);
    });

    expect(authApi.logout).toHaveBeenCalledOnce();
    expect(broadcastAuthSessionChange).toHaveBeenCalledOnce();
  });

  it("resets the idle timer on user activity and coordinates activity across tabs", async () => {
    render(<SessionActivityMonitor />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    act(() => window.dispatchEvent(new Event("pointerdown")));
    expect(authApi.recordActivity).toHaveBeenCalledOnce();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTH_IDLE_TIMEOUT_MS - 1_000);
    });
    expect(authApi.logout).not.toHaveBeenCalled();

    const crossTabActivity = String(Date.now());
    act(() =>
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: "cns.auth-activity",
          newValue: crossTabActivity,
        }),
      ),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTH_IDLE_TIMEOUT_MS - 1);
    });
    expect(authApi.logout).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2);
    });
    expect(authApi.logout).toHaveBeenCalledOnce();
  });

  it("logs out when the server reports that the session has expired", async () => {
    authApi.recordActivity.mockRejectedValueOnce(
      Object.assign(new Error("Session expired"), { status: 401 }),
    );
    render(<SessionActivityMonitor />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
      window.dispatchEvent(new Event("pointerdown"));
      await Promise.resolve();
    });

    expect(authApi.logout).toHaveBeenCalledOnce();
    expect(broadcastAuthSessionChange).toHaveBeenCalledOnce();
  });
});
