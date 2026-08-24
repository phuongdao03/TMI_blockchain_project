export const SUBMISSION_ROLES = ["USER"] as const;

export type WorkspacePersona = "VIEWER" | "USER" | "MODERATOR" | "SUPER_ADMIN";

export function hasAnyRole(
  roles: readonly string[],
  allowed: readonly string[],
): boolean {
  return allowed.some((role) => roles.includes(role));
}

export function resolveDefaultWorkspace(roles: readonly string[]): string {
  if (roles.includes("SUPER_ADMIN")) return "/admin";
  if (roles.includes("MODERATOR")) return "/reviews";
  return "/dashboard";
}

export function resolveWorkspacePersona(
  roles: readonly string[],
): WorkspacePersona {
  if (roles.includes("SUPER_ADMIN")) return "SUPER_ADMIN";
  if (roles.includes("MODERATOR")) return "MODERATOR";
  if (hasAnyRole(roles, SUBMISSION_ROLES)) return "USER";
  return "VIEWER";
}

export function resolvePublicHeaderAction(roles: readonly string[]): {
  href: string;
  label: string;
} {
  const persona = resolveWorkspacePersona(roles);
  if (persona === "VIEWER")
    return { href: "/dashboard", label: "Không gian của tôi" };
  if (persona === "USER") return { href: "/dossiers", label: "Hồ sơ của tôi" };
  if (persona === "MODERATOR")
    return { href: "/reviews", label: "Khu vực thẩm định" };
  return { href: resolveDefaultWorkspace(roles), label: "Quản trị nội bộ" };
}
