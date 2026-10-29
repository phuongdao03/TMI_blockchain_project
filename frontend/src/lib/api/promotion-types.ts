export type CampaignStatus =
  | "DRAFT"
  | "SCHEDULED"
  | "ACTIVE"
  | "PAUSED"
  | "ENDED"
  | "ARCHIVED";
export type PromotionAudience = {
  mode: "ALL" | "ANY";
  registeredBefore: string | null;
  registeredAfter: string | null;
  membershipTiers: string[];
  userIds: string[];
  purchaseHistory: "ANY" | "FIRST" | "RETURNING";
};
export type PromotionPresentation = {
  template: "GIFT" | "PREMIUM" | "MINIMAL" | "LIMITED";
  theme: "CLASSIC" | "LIGHT" | "PREMIUM" | "MINIMAL";
  subtitle: string;
  primaryCta: string;
  secondaryCta: string;
  altText: string;
  imageAssetId: string | null;
  mobileImageAssetId: string | null;
  cardImageAssetId: string | null;
  thumbnailAssetId: string | null;
  imageFit: "contain" | "cover";
  focalX: number;
  focalY: number;
  backgroundColor: string;
  textColor: string;
  ctaColor: string;
  borderRadius: number;
  overlay: number;
  trigger:
    | "LOGIN"
    | "DASHBOARD"
    | "ISSUED"
    | "CHECKOUT"
    | "NOTIFICATION"
    | "BANNER";
  frequency: "ONCE" | "SESSION" | "LIMITED";
  maxViews: number;
  cooldownHours: number;
  enabled: boolean;
  notifyInApp: boolean;
};
export type PromotionPolicy = {
  discountType: "FIXED" | "PERCENT";
  percentageBps: number;
  discountCapVnd: number | null;
  minimumOrderVnd: number;
  maximumOrderVnd: number | null;
  serviceCodes: string[];
  productIds: string[];
  firstOrderOnly: boolean;
  subsequentOrderOnly: boolean;
  stackingPolicy: "NONE" | "BEST" | "MEMBERSHIP_FIRST";
  budgetVnd: number | null;
  issuanceLimit: number | null;
  redemptionLimit: number | null;
  usesPerVoucher: number;
  vouchersPerUser?: number;
  dailyLimit: number | null;
  userDiscountLimitVnd: number | null;
  fixedExpiresAt: string | null;
  allowUseAfterEnd: boolean;
  restoreOnRefund: boolean;
  publicCode?: string | null;
  audience: PromotionAudience;
  presentation: PromotionPresentation;
};
export type CampaignInput = {
  code: string;
  name: string;
  internalDescription: string;
  title: string;
  description: string;
  terms: string;
  imagePath: string;
  amountVnd: number;
  validityDays: number;
  startsAt: string | null;
  endsAt: string | null;
  programType: "AUTO" | "CLAIM" | "CODE" | "MANUAL" | "FIRST_ORDER";
  policy: PromotionPolicy;
};
export type PromotionCampaign = CampaignInput & {
  id: string;
  status: CampaignStatus;
  policyVersion: number;
  createdAt: string;
  updatedAt: string;
  budgetReservedVnd: number;
  budgetSpentVnd: number;
};
export type PromotionPage<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
};
export type PromotionMedia = {
  id: string;
  url: string;
  mimeType: string;
  width: number;
  height: number;
  size: number;
  altText: string;
};
export type AudiencePreview = {
  eligibleCount: number;
  excludedCount: number;
  nominalValueVnd: number;
  exclusionReasons: Record<string, number>;
  sample: { id: string; email: string; reason: string }[];
  previewToken: string;
};
export type DistributionJob = {
  id: string;
  status: string;
  total: number;
  processed: number;
  issued: number;
  failed: number;
  errors?: { userId: string; reason: string }[];
  createdAt?: string;
};
export type PromotionStats = {
  campaignCount: number;
  activeCampaignCount: number;
  issuedCount: number;
  availableCount: number;
  redeemedCount: number;
  expiredCount: number;
  issuedValueVnd: number;
  reservedVnd: number;
  discountVnd: number;
  revenueVnd: number;
  budgetRemainingVnd: number | null;
  viewCount: number;
  clickCount: number;
  daily?: { date: string; issued: number; redeemed: number }[];
  transactions?: PromotionTransaction[];
};
export type PromotionTransaction = {
  id: string;
  voucherId?: string;
  orderId: string;
  campaignId: string;
  discountVnd: number;
  revenueVnd?: number;
  status: string;
  createdAt?: string;
  redeemedAt?: string;
};
export type PromotionAudit = {
  id: string;
  action: string;
  actorUserId?: string;
  campaignId?: string;
  createdAt: string;
};
export const newCampaign = (): CampaignInput => ({
  code: "",
  name: "",
  internalDescription: "",
  title: "",
  description: "",
  terms: "Không quy đổi thành tiền mặt.",
  imagePath: "/images/promotions/golden-voucher.png",
  amountVnd: 200000,
  validityDays: 60,
  startsAt: null,
  endsAt: null,
  programType: "CLAIM",
  policy: {
    discountType: "FIXED",
    percentageBps: 1000,
    discountCapVnd: null,
    minimumOrderVnd: 0,
    maximumOrderVnd: null,
    serviceCodes: ["DOSSIER_SUBMISSION"],
    productIds: [],
    firstOrderOnly: false,
    subsequentOrderOnly: false,
    stackingPolicy: "NONE",
    budgetVnd: null,
    issuanceLimit: null,
    redemptionLimit: null,
    usesPerVoucher: 1,
    dailyLimit: null,
    userDiscountLimitVnd: null,
    fixedExpiresAt: null,
    allowUseAfterEnd: true,
    restoreOnRefund: false,
    audience: {
      mode: "ALL",
      registeredBefore: null,
      registeredAfter: null,
      membershipTiers: [],
      userIds: [],
      purchaseHistory: "ANY",
    },
    presentation: {
      template: "GIFT",
      theme: "LIGHT",
      subtitle: "Món quà tri ân",
      primaryCta: "Sử dụng ưu đãi",
      secondaryCta: "Để sau",
      altText: "Voucher Tinh Hoa Việt",
      imageAssetId: null,
      mobileImageAssetId: null,
      cardImageAssetId: null,
      thumbnailAssetId: null,
      imageFit: "contain",
      focalX: 50,
      focalY: 50,
      backgroundColor: "#fff9ed",
      textColor: "#671b16",
      ctaColor: "#9d0000",
      borderRadius: 16,
      overlay: 0.7,
      trigger: "LOGIN",
      frequency: "ONCE",
      maxViews: 1,
      cooldownHours: 24,
      enabled: true,
      notifyInApp: true,
    },
  },
});
