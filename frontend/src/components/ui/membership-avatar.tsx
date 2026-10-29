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

  return (
    <span
      aria-label={
        showFrame ? `Hạng ${membershipTierPalette[tier].name}` : undefined
      }
      role={showFrame ? "group" : undefined}
      className={cn(
        "relative inline-grid shrink-0 place-items-center rounded-full",
        className,
      )}
      style={{
        height: size,
        width: size,
      }}
    >
      <UserAvatar {...avatarProps} className="border-0" size={avatarSize} />
      {showFrame ? (
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
