"use client";

import { useQuery } from "@tanstack/react-query";

import { UserAvatar } from "@/components/ui/user-avatar";
import { MembershipAvatar } from "@/components/ui/membership-avatar";
import { membershipApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import { canUsePersonalMembership } from "./membership-access";

export function MembershipAccountAvatar({
  user,
  displayName,
  src,
  size,
  className,
}: {
  user: AuthUser;
  displayName: string;
  src?: string | null;
  size: number;
  className?: string;
}) {
  const canShowTier = canUsePersonalMembership(user);
  const membership = useQuery({
    queryKey: ["membership", user.id],
    queryFn: membershipApi.overview,
    enabled: canShowTier,
    staleTime: 30_000,
  });

  if (!canShowTier || !membership.data) {
    return (
      <UserAvatar
        className={className}
        displayName={displayName}
        size={size}
        src={src}
      />
    );
  }

  return (
    <MembershipAvatar
      className={className}
      displayName={displayName}
      size={size}
      src={src}
      tier={membership.data.tier}
    />
  );
}
