import type { CSSProperties } from "react";

import type { MembershipTier } from "@/lib/api/types";

export const membershipTierPalette: Record<
  MembershipTier,
  {
    name: string;
    frame: "bronze" | "silver" | "gold" | "diamond";
    accent: string;
    border: string;
    ink: string;
    surface: string;
    cardStart: string;
    cardMid: string;
    cardEnd: string;
  }
> = {
  MEMBER: {
    name: "Đồng",
    frame: "bronze",
    accent: "#9a4f22",
    border: "#b86f43",
    ink: "#543219",
    surface: "#f2e3d7",
    cardStart: "#faf4ee",
    cardMid: "#e7ccb8",
    cardEnd: "#f4e6db",
  },
  SILVER: {
    name: "Bạc",
    frame: "silver",
    accent: "#87939b",
    border: "#a8b2b9",
    ink: "#37434b",
    surface: "#e2e7ea",
    cardStart: "#f8fafb",
    cardMid: "#dce2e6",
    cardEnd: "#f0f3f5",
  },
  COMPANION: {
    name: "Vàng",
    frame: "gold",
    accent: "#bd8610",
    border: "#cbb273",
    ink: "#51401e",
    surface: "#f7ebc9",
    cardStart: "#fcf5dc",
    cardMid: "#e8d7a6",
    cardEnd: "#f8ebc4",
  },
  PRESTIGE: {
    name: "Kim cương",
    frame: "diamond",
    accent: "#438ca8",
    border: "#8db3c4",
    ink: "#243b47",
    surface: "#dff0f5",
    cardStart: "#f6fbfd",
    cardMid: "#d5e8ef",
    cardEnd: "#edf7fa",
  },
};

type MembershipStyle = CSSProperties & {
  "--membership-accent": string;
  "--membership-border": string;
  "--membership-ink": string;
  "--membership-surface": string;
  "--membership-card-start": string;
  "--membership-card-mid": string;
  "--membership-card-end": string;
};

export function membershipTierStyle(tier: MembershipTier): MembershipStyle {
  const palette = membershipTierPalette[tier];
  return {
    "--membership-accent": palette.accent,
    "--membership-border": palette.border,
    "--membership-ink": palette.ink,
    "--membership-surface": palette.surface,
    "--membership-card-start": palette.cardStart,
    "--membership-card-mid": palette.cardMid,
    "--membership-card-end": palette.cardEnd,
  };
}
