import { Award, BadgeCheck, Gem, HeartHandshake, Sprout } from "lucide-react";
import Image from "next/image";

import { MembershipAvatar } from "@/components/ui/membership-avatar";
import type { MembershipState, MembershipTier } from "@/lib/api/types";
import styles from "./member-card.module.css";
import {
  membershipTierPalette,
  membershipTierStyle,
} from "./membership-tier-palette";

export const membershipTiers = {
  MEMBER: {
    name: membershipTierPalette.MEMBER.name,
    icon: Sprout,
    room: "Sảnh cộng đồng",
  },
  SILVER: {
    name: membershipTierPalette.SILVER.name,
    icon: Award,
    room: "Sảnh cộng đồng",
  },
  COMPANION: {
    name: membershipTierPalette.COMPANION.name,
    icon: HeartHandshake,
    room: "Phòng Đồng hành",
  },
  PRESTIGE: {
    name: membershipTierPalette.PRESTIGE.name,
    icon: Gem,
    room: "Phòng Tinh hoa",
  },
} satisfies Record<
  MembershipTier,
  {
    name: string;
    icon: typeof Sprout;
    room: string;
  }
>;

export function MemberCard({
  membership,
  name,
  avatarUrl,
}: {
  membership: MembershipState;
  name: string;
  avatarUrl?: string | null;
}) {
  const tier = membershipTiers[membership.tier];
  const Icon = tier.icon;
  return (
    <article
      className={styles.card}
      data-tier={membership.tier}
      aria-label={`Thẻ ${tier.name} của ${name}`}
      style={membershipTierStyle(membership.tier)}
    >
      <span className={styles.motif} aria-hidden="true" />
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Image
            src="/assets/brand/logo-tinh-hoa-viet.png"
            className="shrink-0 rounded-full object-contain"
            width={38}
            height={38}
            alt=""
          />
          <div>
            <p className="text-xs font-bold tracking-[0.18em]">TINH HOA VIỆT</p>
            <p className="mt-1 text-xs opacity-75">CỘNG ĐỒNG THÀNH VIÊN</p>
          </div>
        </div>
        <BadgeCheck
          aria-label="Thẻ đang có hiệu lực"
          className="size-6 shrink-0"
        />
      </div>
      <div className="mt-9 flex items-center gap-3">
        <MembershipAvatar
          displayName={name}
          src={avatarUrl}
          size={44}
          tier={membership.tier}
        />
        <p className="min-w-0 break-words text-lg font-bold sm:text-xl">
          {name}
        </p>
      </div>
      <div className="mt-6 flex items-center gap-3">
        <Icon aria-hidden="true" className="size-8" />
        <div>
          <p className="text-xs uppercase tracking-[0.15em] opacity-75">
            Hạng thẻ
          </p>
          <h2 className="mt-1 text-2xl font-semibold">{tier.name}</h2>
        </div>
      </div>
      <div className={`${styles.rule} mt-6`} />
      <div className="mt-4 flex flex-wrap justify-between gap-3 text-xs">
        <p className="max-w-full break-all font-mono tracking-wider">
          {membership.memberNumber}
        </p>
        <p>
          {membership.expiresAt
            ? `Hiệu lực đến ${new Date(membership.expiresAt).toLocaleDateString("vi-VN")}`
            : "Thành viên cộng đồng"}
        </p>
      </div>
    </article>
  );
}
