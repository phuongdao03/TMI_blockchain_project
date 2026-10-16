export const AUTH_SESSION_CHANGE_KEY = "cns.auth-session-change";

export function broadcastAuthSessionChange(): void {
  try {
    window.localStorage.setItem(
      AUTH_SESSION_CHANGE_KEY,
      `${Date.now()}-${Math.random()}`,
    );
  } catch {
    // Cookie-backed auth remains usable when browser storage is unavailable.
  }
}

export function subscribeToAuthSessionChanges(
  listener: () => void,
): () => void {
  const handleStorage = (event: StorageEvent) => {
    if (event.key === AUTH_SESSION_CHANGE_KEY) listener();
  };
  window.addEventListener("storage", handleStorage);
  return () => window.removeEventListener("storage", handleStorage);
}
