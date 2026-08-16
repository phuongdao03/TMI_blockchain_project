export type ReleaseMode = "preview" | "full";

const restrictedPrefixes = [
  "/admin",
  "/activity",
  "/certificates",
  "/council",
  "/dossiers",
  "/notifications",
  "/payments",
  "/reviews",
  "/vote-history",
] as const;

export function releaseMode(value?: string): ReleaseMode {
  if (value !== undefined) return value === "full" ? "full" : "preview";
  const configured = process.env.NEXT_PUBLIC_RELEASE_MODE;
  if (configured !== undefined) {
    return configured === "full" ? "full" : "preview";
  }
  return process.env.NODE_ENV === "production" ? "preview" : "full";
}

export function isPreviewRelease(value?: string): boolean {
  return releaseMode(value) === "preview";
}

export function isPreviewRestrictedPath(pathname: string): boolean {
  return restrictedPrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
