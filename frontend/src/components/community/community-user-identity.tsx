import { BadgeCheck } from "lucide-react";
import Link from "next/link";

import { MembershipAvatar } from "@/components/ui/membership-avatar";
import type { CommunityAuthor, MembershipTier } from "@/lib/api/types";

const membershipLabels: Record<MembershipTier, string> = {
  MEMBER: "Đồng",
  SILVER: "Bạc",
  COMPANION: "Vàng",
  PRESTIGE: "Kim cương",
};

const membershipStyles: Record<MembershipTier, string> = {
  MEMBER: "border-slate-300 bg-slate-100 text-slate-700",
  SILVER: "border-gray-400/60 bg-gray-200 text-gray-800",
  COMPANION: "border-amber-600/40 bg-amber-100 text-amber-950",
  PRESTIGE: "border-sky-700/40 bg-sky-100 text-sky-950",
};

const avatarStyles: Record<MembershipTier, string> = {
  MEMBER: "",
  SILVER:
    "ring-2 ring-gray-400/80 ring-offset-1 ring-offset-[var(--theme-surface)]",
  COMPANION:
    "ring-2 ring-amber-500/70 ring-offset-1 ring-offset-[var(--theme-surface)]",
  PRESTIGE:
    "ring-2 ring-sky-600/70 ring-offset-1 ring-offset-[var(--theme-surface)]",
};

export function CommunityUserIdentity({
  user,
  size = 34,
}: {
  user: CommunityAuthor;
  size?: number;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <MembershipAvatar
        displayName={user.displayName}
        size={size}
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
          <CommunityMembershipBadge tier={user.membershipTier ?? "MEMBER"} />
        </div>
        <CommunityRoleBadge isAdmin={user.isAdmin} roleLabel={user.roleLabel} />
      </div>
    </div>
  );
}

export function CommunityMembershipBadge({ tier }: { tier: MembershipTier }) {
  return (
    <span
      aria-label={`Hạng thẻ ${membershipLabels[tier]}`}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold leading-4 ${membershipStyles[tier]}`}
    >
      <span aria-hidden="true">✦</span>
      {membershipLabels[tier]}
    </span>
  );
}

export function communityAvatarTierClass(tier?: MembershipTier): string {
  return avatarStyles[tier ?? "MEMBER"];
}

export function getAuthenticatedCommunityIdentity({
  displayName,
  roles = [],
}: {
  displayName?: string | null;
  roles?: readonly string[];
}) {
  const isAdmin = roles.includes("SUPER_ADMIN");
  const isModerator = !isAdmin && roles.includes("MODERATOR");
  return {
    displayName:
      displayName?.trim() || (isAdmin ? "Quản trị viên THV" : "Thành viên"),
    isAdmin,
    roleLabel: isAdmin
      ? "Quản trị viên"
      : isModerator
        ? "Thẩm định viên"
        : null,
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
