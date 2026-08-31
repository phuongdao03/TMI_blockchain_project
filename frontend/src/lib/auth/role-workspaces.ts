export const SUBMISSION_ROLES = ["USER"] as const;

export type WorkspacePersona = "VIEWER" | "USER" | "MODERATOR" | "SUPER_ADMIN";

export function hasAnyRole(
  roles: readonly string[],
  allowed: readonly string[],
): boolean {
  return allowed.some((role) => roles.includes(role));
}

const OPERATIONAL_WORKSPACES: ReadonlyArray<readonly [string, string]> = [
  ["payments.read", "/admin/payments"],
  ["dashboard.read", "/admin/dashboard"],
  ["users.read", "/admin/users"],
  ["staff.read", "/admin/staff"],
  ["audit.read", "/admin/audit"],
  ["reports.read", "/admin/reports"],
  ["submissions.approve", "/council"],
  ["blockchain.sign", "/blockchain"],
];

export function resolveDefaultWorkspace(
  roles: readonly string[],
  permissions: readonly string[] = [],
): string {
  if (roles.includes("SUPER_ADMIN")) return "/admin";
  const assignedWorkspace = OPERATIONAL_WORKSPACES.find(([permission]) =>
    permissions.includes(permission),
  );
  if (assignedWorkspace) return assignedWorkspace[1];
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

export function resolvePublicHeaderAction(
  roles: readonly string[],
  permissions: readonly string[] = [],
): {
  href: string;
  label: string;
} {
  const persona = resolveWorkspacePersona(roles);
  if (persona === "VIEWER")
    return { href: "/dashboard", label: "Không gian của tôi" };
  if (persona === "USER" && permissions.length === 0)
    return { href: "/dossiers", label: "Hồ sơ của tôi" };
  if (persona === "MODERATOR")
    return { href: "/reviews", label: "Khu vực thẩm định" };
  return {
    href: resolveDefaultWorkspace(roles, permissions),
    label: "Quay lại khu vực làm việc",
  };
}
