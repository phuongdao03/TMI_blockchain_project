export const AUTH_SESSION_CHANGE_KEY = "cns.auth-session-change";
const AUTH_SESSION_CHANGE_EVENT = "cns:auth-session-change";

export function broadcastAuthSessionChange(): void {
  try {
    window.localStorage.setItem(
      AUTH_SESSION_CHANGE_KEY,
      `${Date.now()}-${Math.random()}`,
    );
  } catch {
    // Cookie-backed auth remains usable when browser storage is unavailable.
  }
  window.dispatchEvent(new Event(AUTH_SESSION_CHANGE_EVENT));
}

export function subscribeToAuthSessionChanges(
  listener: () => void,
): () => void {
  const handleStorage = (event: StorageEvent) => {
    if (event.key === AUTH_SESSION_CHANGE_KEY) listener();
  };
  window.addEventListener("storage", handleStorage);
  window.addEventListener(AUTH_SESSION_CHANGE_EVENT, listener);
  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(AUTH_SESSION_CHANGE_EVENT, listener);
  };
}
