import { BadgeCheck } from "lucide-react";
import Link from "next/link";

import { membershipTierPalette } from "@/components/membership/membership-tier-palette";
import { MembershipAvatar } from "@/components/ui/membership-avatar";
import type { CommunityAuthor, MembershipTier } from "@/lib/api/types";

export function CommunityUserIdentity({
  user,
  size = 34,
}: {
  user: CommunityAuthor;
  size?: number;
}) {
  const isMembershipStaff = isMembershipStaffIdentity(user);
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <MembershipAvatar
        displayName={user.displayName}
        size={size}
        showFrame={!isMembershipStaff}
        src={user.avatarUrl}
        tier={user.membershipTier ?? "MEMBER"}
      />
      <div className="flex min-w-0 flex-col items-start gap-1">
        <div className="flex max-w-full flex-wrap items-center gap-1.5">
          <Link
            className="max-w-full truncate font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href={`/community/members/${encodeURIComponent(user.username)}`}
          >
            {user.displayName?.trim() || "Thành viên"}
          </Link>
          <CommunityMembershipBadge
            isMembershipStaff={isMembershipStaff}
            tier={user.membershipTier ?? "MEMBER"}
          />
        </div>
        <CommunityRoleBadge isAdmin={user.isAdmin} roleLabel={user.roleLabel} />
      </div>
    </div>
  );
}

export function CommunityMembershipBadge({
  tier,
  isMembershipStaff = false,
}: {
  tier: MembershipTier;
  isMembershipStaff?: boolean;
}) {
  if (isMembershipStaff) return null;
  const palette = membershipTierPalette[tier];
  return (
    <span
      aria-label={`Hạng thẻ ${palette.name}`}
      className="inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold leading-4"
      style={{
        borderColor: palette.border,
        backgroundColor: palette.surface,
        color: palette.ink,
      }}
    >
      <span aria-hidden="true">✦</span>
      {palette.name}
    </span>
  );
}

export function isMembershipStaffIdentity(
  user: Pick<CommunityAuthor, "isAdmin" | "roleLabel">,
): boolean {
  return (
    user.isAdmin === true ||
    user.roleLabel === "Quản trị viên" ||
    user.roleLabel === "Quản lý hội viên"
  );
}

export function getAuthenticatedCommunityIdentity({
  displayName,
  roles = [],
  permissions = [],
}: {
  displayName?: string | null;
  roles?: readonly string[];
  permissions?: readonly string[];
}) {
  const isAdmin = roles.includes("SUPER_ADMIN");
  const isModerator = !isAdmin && roles.includes("MODERATOR");
  const isMembershipManager = permissions.includes("memberships.manage");
  const roleLabel = isAdmin
    ? "Quản trị viên"
    : isMembershipManager
      ? "Quản lý hội viên"
      : isModerator
        ? "Thẩm định viên"
        : null;
  return {
    displayName:
      displayName?.trim() || (isAdmin ? "Quản trị viên THV" : "Thành viên"),
    isAdmin,
    roleLabel,
  };
}

export function CommunityRoleBadge({
  isAdmin,
  roleLabel,
}: {
  isAdmin?: boolean;
  roleLabel?: string | null;
}) {
  if (!roleLabel) return null;
  return (
    <span
      className={
        isAdmin
          ? "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-[var(--theme-accent)]/35 bg-[var(--theme-accent)]/10 px-2 py-0.5 text-[11px] font-bold text-[var(--theme-accent)]"
          : "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-[var(--theme-border)] px-2 py-0.5 text-[11px] font-semibold text-[var(--theme-muted)]"
      }
    >
      {isAdmin ? <BadgeCheck aria-hidden="true" className="size-3.5" /> : null}
      {roleLabel}
    </span>
  );
}
