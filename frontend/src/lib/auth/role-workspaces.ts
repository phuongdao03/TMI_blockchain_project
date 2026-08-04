export const APPLICANT_ROLES = ["APPLICANT", "ORG_MANAGER"] as const;

export type WorkspacePersona =
  | "PUBLIC"
  | "APPLICANT"
  | "REVIEWER"
  | "COUNCIL"
  | "ADMIN"
  | "SUPER_ADMIN";

export function hasAnyRole(
  roles: readonly string[],
  allowed: readonly string[],
): boolean {
  return allowed.some((role) => roles.includes(role));
}

export function resolveDefaultWorkspace(roles: readonly string[]): string {
  if (roles.includes("SUPER_ADMIN")) return "/admin/dashboard";
  if (roles.includes("CONTENT_ADMIN")) return "/admin/noi-dung";
  if (roles.includes("FINANCE_ADMIN")) return "/admin/dashboard";
  if (roles.includes("BLOCKCHAIN_ADMIN")) return "/admin/dashboard";
  if (hasAnyRole(roles, ["COUNCIL_SECRETARY", "COUNCIL_MEMBER"]))
    return "/hoi-dong";
  if (roles.includes("REVIEWER")) return "/tham-dinh";
  return "/dashboard";
}

export function resolveWorkspacePersona(
  roles: readonly string[],
): WorkspacePersona {
  if (roles.includes("SUPER_ADMIN")) return "SUPER_ADMIN";
  if (
    hasAnyRole(roles, ["CONTENT_ADMIN", "FINANCE_ADMIN", "BLOCKCHAIN_ADMIN"])
  ) {
    return "ADMIN";
  }
  if (hasAnyRole(roles, ["COUNCIL_SECRETARY", "COUNCIL_MEMBER"])) {
    return "COUNCIL";
  }
  if (roles.includes("REVIEWER")) return "REVIEWER";
  if (hasAnyRole(roles, APPLICANT_ROLES)) return "APPLICANT";
  return "PUBLIC";
}
