export const AUTH_ACTIVITY_CHANGE_KEY = "cns.auth-activity";
const AUTH_ACTIVITY_EVENT = "cns:auth-activity";

export function broadcastUserActivity(timestamp = Date.now()): void {
  const safeTimestamp = Math.min(timestamp, Date.now());
  try {
    window.localStorage.setItem(
      AUTH_ACTIVITY_CHANGE_KEY,
      String(safeTimestamp),
    );
  } catch {
    // The backend remains authoritative when browser storage is unavailable.
  }
  window.dispatchEvent(
    new CustomEvent(AUTH_ACTIVITY_EVENT, { detail: safeTimestamp }),
  );
}

export function subscribeToUserActivity(
  listener: (timestamp: number) => void,
): () => void {
  const handleStorage = (event: StorageEvent) => {
    if (event.key !== AUTH_ACTIVITY_CHANGE_KEY || event.newValue === null)
      return;
    const timestamp = Number(event.newValue);
    if (Number.isFinite(timestamp)) listener(timestamp);
  };
  const handleActivity = (event: Event) => {
    const timestamp = (event as CustomEvent<number>).detail;
    if (Number.isFinite(timestamp)) listener(timestamp);
  };
  window.addEventListener("storage", handleStorage);
  window.addEventListener(AUTH_ACTIVITY_EVENT, handleActivity);
  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(AUTH_ACTIVITY_EVENT, handleActivity);
  };
}
