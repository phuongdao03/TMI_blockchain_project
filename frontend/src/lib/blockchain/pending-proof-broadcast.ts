export interface PendingProofBroadcast {
  dossierId: string;
  version: number;
  transactionId: string;
  intentId: string;
  transactionHash: string;
  connectedWallet: string;
}

const prefix = "thv-proof-broadcast:";

function key(dossierId: string, version: number): string {
  return `${prefix}${dossierId}:${version}`;
}

export function readPendingProofBroadcast(
  dossierId: string,
  version: number,
): PendingProofBroadcast | null {
  try {
    const stored = window.localStorage.getItem(key(dossierId, version));
    if (!stored) return null;
    const value = JSON.parse(stored) as PendingProofBroadcast;
    return value.dossierId === dossierId &&
      value.version === version &&
      typeof value.transactionId === "string" &&
      typeof value.intentId === "string" &&
      /^0x[0-9a-fA-F]{64}$/.test(value.transactionHash) &&
      /^0x[0-9a-fA-F]{40}$/.test(value.connectedWallet)
      ? value
      : null;
  } catch {
    return null;
  }
}

export function savePendingProofBroadcast(value: PendingProofBroadcast): void {
  try {
    window.localStorage.setItem(
      key(value.dossierId, value.version),
      JSON.stringify(value),
    );
  } catch {
    // A blocked or full local storage must not prevent submitting the hash.
  }
}

export function clearPendingProofBroadcast(value: PendingProofBroadcast): void {
  try {
    const current = readPendingProofBroadcast(value.dossierId, value.version);
    if (current?.transactionHash === value.transactionHash) {
      window.localStorage.removeItem(key(value.dossierId, value.version));
    }
  } catch {
    // The backend transaction record remains authoritative.
  }
}
