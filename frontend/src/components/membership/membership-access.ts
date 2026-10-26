import type { AuthUser } from "@/lib/api/types";

type MembershipIdentity = Pick<AuthUser, "roles" | "permissions">;

export function canUsePersonalMembership(
  user: MembershipIdentity | null | undefined,
): boolean {
  if (!user) return false;
  return (
    !user.roles.includes("SUPER_ADMIN") &&
    !user.permissions?.includes("memberships.manage")
  );
}
