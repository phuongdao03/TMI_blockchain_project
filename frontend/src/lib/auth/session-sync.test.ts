import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_SESSION_CHANGE_KEY,
  broadcastAuthSessionChange,
  subscribeToAuthSessionChanges,
} from "@/lib/auth/session-sync";

describe("session change notifications", () => {
  afterEach(() => vi.restoreAllMocks());

  it("notifies subscribers in the tab that completed authentication", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeToAuthSessionChanges(listener);
    try {
      broadcastAuthSessionChange();
      expect(listener).toHaveBeenCalledTimes(1);
      unsubscribe();
      broadcastAuthSessionChange();
      expect(listener).toHaveBeenCalledTimes(1);
    } finally {
      unsubscribe();
    }
  });

  it("still notifies the active tab when browser storage is unavailable", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });
    const listener = vi.fn();
    const unsubscribe = subscribeToAuthSessionChanges(listener);
    try {
      broadcastAuthSessionChange();
      expect(listener).toHaveBeenCalledTimes(1);
    } finally {
      unsubscribe();
    }
  });

  it("reacts only to cross-tab session changes and removes its listener", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeToAuthSessionChanges(listener);
    window.dispatchEvent(new StorageEvent("storage", { key: "unrelated" }));
    expect(listener).not.toHaveBeenCalled();
    window.dispatchEvent(
      new StorageEvent("storage", { key: AUTH_SESSION_CHANGE_KEY }),
    );
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
    window.dispatchEvent(
      new StorageEvent("storage", { key: AUTH_SESSION_CHANGE_KEY }),
    );
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
