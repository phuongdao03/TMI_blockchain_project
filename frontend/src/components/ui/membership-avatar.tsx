import Image from "next/image";

import { UserAvatar } from "@/components/ui/user-avatar";
import { cn } from "@/lib/utils";
import type { MembershipTier } from "@/lib/api/types";

const frameByTier: Record<MembershipTier, string> = {
  MEMBER: "bronze",
  SILVER: "silver",
  COMPANION: "gold",
  PRESTIGE: "diamond",
};
const compactFrameClass: Record<MembershipTier, string> = {
  MEMBER:
    "ring-2 ring-amber-700/70 ring-offset-1 ring-offset-[var(--theme-surface)]",
  SILVER:
    "ring-2 ring-slate-400 ring-offset-1 ring-offset-[var(--theme-surface)]",
  COMPANION:
    "ring-2 ring-amber-500 ring-offset-1 ring-offset-[var(--theme-surface)]",
  PRESTIGE:
    "ring-2 ring-sky-600 ring-offset-1 ring-offset-[var(--theme-surface)]",
};

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
  const frame = frameByTier[tier];
  const compact = size < 36;

  return (
    <span
      className={cn(
        "relative inline-grid shrink-0 place-items-center rounded-full",
        showFrame && compact ? compactFrameClass[tier] : "",
        className,
      )}
      style={{ height: size, width: size }}
    >
      <UserAvatar {...avatarProps} className="border-0" size={avatarSize} />
      {showFrame && !compact ? (
        <Image
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-10 size-full object-contain"
          fill
          sizes={`${size}px`}
          src={`/assets/membership/avatar-frames/${frame}.png`}
        />
      ) : null}
    </span>
  );
}
