import Image from "next/image";

import { membershipTierPalette } from "@/components/membership/membership-tier-palette";
import { UserAvatar } from "@/components/ui/user-avatar";
import { cn } from "@/lib/utils";
import type { MembershipTier } from "@/lib/api/types";

export function MembershipAvatar({
  tier,
  size = 40,
  showFrame = true,
  className,
  ...avatarProps
}: {
  tier: MembershipTier;
  displayName?: string | null;
  src?: string | null;
  size?: number;
  showFrame?: boolean;
  className?: string;
}) {
  const avatarSize = Math.round(size * 0.72);
  const compact = size < 36;

  return (
    <span
      className={cn(
        "relative inline-grid shrink-0 place-items-center rounded-full",
        className,
      )}
      style={{
        height: size,
        width: size,
        boxShadow:
          showFrame && compact
            ? `0 0 0 2px ${membershipTierPalette[tier].accent}`
            : undefined,
      }}
    >
      <UserAvatar {...avatarProps} className="border-0" size={avatarSize} />
      {showFrame && !compact ? (
        <Image
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-10 size-full object-contain"
          fill
          sizes={`${size}px`}
          src={`/assets/membership/avatar-frames/${membershipTierPalette[tier].frame}.png`}
        />
      ) : null}
    </span>
  );
}
