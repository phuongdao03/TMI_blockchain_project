// This must match the default public verification runtime limit. The digest is
// calculated in the browser; the file is not uploaded during this path.
export const MAX_LOCAL_VERIFICATION_BYTES = 25 * 1024 * 1024;

export type LocalFileComparison =
  | { status: "MATCH"; digest: string }
  | { status: "NO_MATCH"; digest: string }
  | { status: "NO_PUBLIC_REFERENCE"; digest: null };

export async function hashLocalFile(file: Blob): Promise<string> {
  if (file.size === 0) throw new Error("The selected file is empty.");
  if (file.size > MAX_LOCAL_VERIFICATION_BYTES) {
    throw new Error("The selected file is too large.");
  }
  if (!globalThis.crypto?.subtle) {
    throw new Error("Secure local hashing is unavailable in this browser.");
  }
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256",
    await file.arrayBuffer(),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export async function compareLocalFile(
  file: Blob,
  publicDigests: readonly string[],
): Promise<LocalFileComparison> {
  const references = publicDigests
    .map((value) => value.trim().toLowerCase())
    .filter((value) => /^[0-9a-f]{64}$/.test(value));
  if (references.length === 0) {
    return { status: "NO_PUBLIC_REFERENCE", digest: null };
  }
  const digest = await hashLocalFile(file);
  return {
    status: references.includes(digest) ? "MATCH" : "NO_MATCH",
    digest,
  };
}
