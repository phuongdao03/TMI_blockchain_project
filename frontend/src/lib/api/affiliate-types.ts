export interface AffiliateSummary {
  referralCode: string;
  referralUrl: string;
  status: string;
  clickCount: number;
  attributedUserCount: number;
  createdAt: string;
  pendingCommissionMinor: number;
  onHoldCommissionMinor: number;
  availableBalanceMinor: number;
  reservedBalanceMinor: number;
  lifetimeEarnedMinor: number;
  totalWithdrawnMinor: number;
  totalReversedMinor: number;
}

export interface AffiliateReferral {
  id: string;
  attributedAt: string;
  expiresAt: string;
  conversionCount: number;
  revenueMinor: number;
  commissionAmountMinor: number;
}

export interface AffiliateCommission {
  id: string;
  serviceCode: string;
  commissionAmountMinor: number;
  status: string;
  earnedAt: string;
}

export interface AdminAffiliateProfile {
  userId: string;
  referralCode: string;
  status: "ACTIVE" | "SUSPENDED";
  createdAt: string;
  clickCount: number;
  attributedUserCount: number;
}

export interface AdminAffiliateCommission {
  id: string;
  affiliateUserId: string;
  referredUserId: string;
  ruleSetVersion: number;
  serviceCode: string;
  sourceReference: string;
  amountMinor: number;
  commissionAmountMinor: number;
  rateBasisPoints: number;
  currency: string;
  status:
    | "PENDING"
    | "ON_HOLD"
    | "AVAILABLE"
    | "REJECTED"
    | "REVERSED"
    | "SUPPRESSED";
  earnedAt: string;
  holdUntil: string;
  approvedAt: string | null;
  reviewedByUserId: string | null;
  reviewReason: string | null;
  reversedAt: string | null;
  reversalReason: string | null;
  createdAt: string;
}

export interface AffiliateCommissionRate {
  serviceCode: string;
  directRateBasisPoints: number;
}

export interface AffiliateCommissionRuleSet {
  id: string;
  versionNo: number;
  status: "DRAFT" | "PUBLISHED" | "RETIRED";
  enabled: boolean;
  attributionWindowDays: number;
  holdDays: number;
  level2Enabled: boolean;
  level2RateBasisPoints: number;
  effectiveFrom: string | null;
  publishedAt: string | null;
  publishedByUserId: string | null;
  rates: AffiliateCommissionRate[];
}

export interface AffiliateCommissionRuleSetInput {
  enabled: boolean;
  attributionWindowDays: number;
  holdDays: number;
  rates: AffiliateCommissionRate[];
}
