export const SUBMISSION_ROLES = ["USER"] as const;

export type WorkspacePersona = "VIEWER" | "USER" | "MODERATOR" | "SUPER_ADMIN";

export function hasAnyRole(
  roles: readonly string[],
  allowed: readonly string[],
): boolean {
  return allowed.some((role) => roles.includes(role));
}

type AdminEntryPoint = readonly [
  permission: string,
  href: string,
  allowedRoles?: readonly string[],
];

const ADMIN_ENTRY_POINTS: readonly AdminEntryPoint[] = [
  ["promotions.manage", "/admin/promotions"],
  ["promotions.read", "/admin/promotions"],
  ["review.assign", "/admin/reviews", ["SUPER_ADMIN"]],
  ["work.allocations.manage", "/admin/work-allocations", ["SUPER_ADMIN"]],
  ["hr.overtime.read", "/admin/overtime"],
  ["hr.leave.read", "/admin/leave"],
  ["hr.attendance.worksites.manage", "/admin/attendance/worksites"],
  ["hr.attendance.read", "/admin/attendance"],
  ["hr.payroll.read", "/admin/payroll"],
  ["hr.employees.read", "/admin/employees"],
  ["hr.departments.manage", "/admin/departments"],
  ["payments.read", "/admin/payments"],
  ["memberships.manage", "/admin/memberships"],
  ["dashboard.read", "/admin/dashboard"],
  ["users.read", "/admin/users"],
  ["staff.read", "/admin/staff"],
  ["audit.read", "/admin/audit"],
  ["reports.read", "/admin/reports"],
  ["public_content.manage", "/admin/content"],
  ["community.moderate", "/admin/community"],
  ["community.manage", "/admin/community"],
];

export function resolveDefaultWorkspace(
  _roles: readonly string[],
  _permissions: readonly string[] = [],
): string {
  void _roles;
  void _permissions;
  return "/workspace";
}

export function resolveWorkspacePersona(
  roles: readonly string[],
): WorkspacePersona {
  if (roles.includes("SUPER_ADMIN")) return "SUPER_ADMIN";
  if (roles.includes("MODERATOR")) return "MODERATOR";
  if (hasAnyRole(roles, SUBMISSION_ROLES)) return "USER";
  return "VIEWER";
}

export function resolveAdminEntryPoint(
  roles: readonly string[],
  permissions: readonly string[] = [],
): { href: string; label: string } | null {
  if (roles.includes("SUPER_ADMIN")) {
    return { href: "/admin", label: "Khu vực quản trị" };
  }

  const entryPoint = ADMIN_ENTRY_POINTS.find(
    ([permission, , allowedRoles]) =>
      permissions.includes(permission) &&
      (!allowedRoles || allowedRoles.some((role) => roles.includes(role))),
  );
  if (!entryPoint) return null;

  return {
    href: entryPoint[1],
    label: "Khu vực quản trị",
  };
}
