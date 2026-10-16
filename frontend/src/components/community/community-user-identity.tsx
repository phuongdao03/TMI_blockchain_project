import { BadgeCheck } from "lucide-react";
import Link from "next/link";

import { UserAvatar } from "@/components/ui/user-avatar";
import type { CommunityAuthor } from "@/lib/api/types";

export function CommunityUserIdentity({
  user,
  size = 34,
}: {
  user: CommunityAuthor;
  size?: number;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <UserAvatar
        className="border-[var(--theme-border)]"
        displayName={user.displayName}
        size={size}
        src={user.avatarUrl}
      />
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <Link
          className="truncate font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href={`/community/members/${encodeURIComponent(user.username)}`}
        >
          {user.displayName?.trim() || "Thành viên"}
        </Link>
        <CommunityRoleBadge
          isAdmin={user.isAdmin}
          roleLabel={user.roleLabel}
        />
      </div>
    </div>
  );
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
    displayName: isAdmin
      ? "Quản trị viên THV"
      : displayName?.trim() || "Thành viên",
    isAdmin,
    roleLabel: isAdmin
      ? "Quản trị viên"
      : isModerator
        ? "Điều hành viên"
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
          ? "inline-flex items-center gap-1 rounded-full border border-[var(--theme-accent)]/35 bg-[var(--theme-accent)]/10 px-2 py-0.5 text-[11px] font-bold text-[var(--theme-accent)]"
          : "inline-flex items-center gap-1 rounded-full border border-[var(--theme-border)] px-2 py-0.5 text-[11px] font-semibold text-[var(--theme-muted)]"
      }
    >
      {isAdmin ? <BadgeCheck aria-hidden="true" className="size-3.5" /> : null}
      {roleLabel}
    </span>
  );
}
