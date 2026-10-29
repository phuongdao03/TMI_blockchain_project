import type { PromotionPolicy } from "./promotion-types";

export type VoucherOffer = {
  id: string;
  title: string;
  description: string;
  terms: string;
  imagePath: string;
  amountVnd: number;
  validityDays: number;
  policy?: PromotionPolicy;
  claimedVoucherId?: string | null;
  expiresAt?: string | null;
};

export type SavedVoucher = Omit<
  VoucherOffer,
  "description" | "validityDays"
> & {
  campaignId: string;
  claimedAt: string;
  expiresAt: string;
  expired: boolean;
  policy?: PromotionPolicy;
  status?: "AVAILABLE" | "RESERVED" | "REDEEMED" | "REVOKED";
  uniqueCode?: string | null;
  validFrom?: string | null;
  redeemedAt?: string | null;
  usesUsed?: number;
};
