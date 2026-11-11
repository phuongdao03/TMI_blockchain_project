export type AdvertisingCampaignStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "PENDING_PAYMENT"
  | "SCHEDULED"
  | "NEEDS_RESCHEDULE"
  | "ACTIVE"
  | "PAUSED"
  | "COMPLETED"
  | "CANCELLED"
  | "REJECTED";

export interface AdvertisingPlacement {
  id: string;
  code: string;
  name: string;
  pageLocation: string;
  deliveryMode: "EQUAL_ROTATION" | "WEIGHTED_ROTATION" | "EXCLUSIVE";
  capacity: number;
  enabled: boolean;
  timezone: string;
}

export interface AdvertisingPackage {
  id: string;
  code: string;
  name: string;
  placementId: string;
  durationHours: number;
  rotationWeight: number;
  basePriceVnd: number;
  priceVersion: number;
  active: boolean;
  terms: string;
}

export interface AdvertisingCampaignSummary {
  id: string;
  dossierId: string;
  packageId: string;
  placementId: string;
  placementCode: string;
  placementName: string;
  purchaseContext: "BEFORE_PUBLICATION" | "AFTER_PUBLICATION";
  status: AdvertisingCampaignStatus;
  desiredStartAt: string | null;
  actualStartAt: string | null;
  actualEndAt: string | null;
  bookingStartAt: string | null;
  bookingEndAt: string | null;
  creativeTitle: string | null;
  creativeDescription?: string | null;
  imageUrl: string | null;
  destinationUrl?: string | null;
  creativeReviewStatus:
    | "PENDING"
    | "APPROVED"
    | "REJECTED"
    | "CHANGES_REQUESTED"
    | null;
  creativeReviewNote: string | null;
  paymentStatus: "PENDING" | "PAID" | "EXPIRED" | "FAILED" | null;
  deliveryCount: number;
  createdAt: string;
}

export interface AdvertisingCampaignCreated {
  campaign: {
    id: string;
    dossierId: string;
    packageId: string;
    placementId: string;
    purchaseContext: "BEFORE_PUBLICATION" | "AFTER_PUBLICATION";
    status: AdvertisingCampaignStatus;
    desiredStartAt: string | null;
    actualStartAt: string | null;
    actualEndAt: string | null;
    deliveryCount: number;
    createdAt: string;
  };
  creativeId: string;
}

export interface AdvertisingCreative {
  id: string;
  campaignId: string;
  version: number;
  title: string;
  description: string;
  imageUrl: string | null;
  destinationUrl: string;
  reviewStatus: string;
  reviewNote: string | null;
}

export interface AdvertisingAvailability {
  placement: AdvertisingPlacement;
  package: AdvertisingPackage;
  startAt: string;
  endAt: string;
  available: boolean;
  remainingSlots: number;
  alternatives: string[];
}

export interface AdvertisingQuote {
  placementCode: string;
  placementName: string;
  packageCode: string;
  packageName: string;
  durationHours: number;
  priceVersion: number;
  membershipTier: string;
  membershipCycleStart: string | null;
  discountPolicyVersion: number;
  discountRateBasisPoints: number;
  remainingDiscountAllowanceVnd: number;
  baseAmountVnd: number;
  discountAmountVnd: number;
  payableAmountVnd: number;
}

export interface AdvertisingReservation {
  id: string;
  campaignId: string;
  placementId: string;
  startAt: string;
  endAt: string;
  expiresAt: string;
  status: "HELD" | "CONFIRMED" | "EXPIRED" | "CANCELLED";
}

export interface AdvertisingOrder {
  id: string;
  reservationId: string;
  campaignId: string;
  membershipTier: string;
  membershipCycleStart: string | null;
  priceVersion: number;
  discountPolicyVersion: number;
  baseAmountVnd: number;
  discountAmountVnd: number;
  payableAmountVnd: number;
  paymentStatus: "PENDING" | "PAID" | "EXPIRED" | "FAILED";
  allowanceExpiresAt: string;
  walletTransactionId: string | null;
  pricingSnapshot: Record<string, unknown>;
  paidAt: string | null;
}

export interface AdvertisingReservationCheckout {
  reservation: AdvertisingReservation;
  order: AdvertisingOrder;
}

export interface AdvertisingWaitlistEntry {
  id: string;
  campaignId: string;
  placementId: string;
  startAt: string;
  endAt: string;
  status: "WAITING" | "NOTIFIED" | "CANCELLED" | "FULFILLED";
  createdAt: string;
}

export interface AdvertisingCampaignMetrics {
  campaignId: string;
  deliveryCount: number;
  validImpressions: number;
  validClicks: number;
  ctrBasisPoints: number;
  actualShareBasisPoints: number;
  targetShareBasisPoints: number;
  activeSeconds: number;
}

export interface AdvertisingReviewQueueItem {
  campaignId: string;
  ownerEmail: string;
  dossierId: string;
  dossierCode: string;
  dossierTitle: string;
  placementCode: string;
  packageName: string;
  campaignStatus: AdvertisingCampaignStatus;
  creativeId: string;
  creativeVersion: number;
  title: string;
  description: string;
  imageUrl: string | null;
  destinationUrl: string;
  reviewStatus: string;
}

export interface AdvertisingAdminInventoryItem {
  id: string;
  campaignId: string;
  ownerEmail: string;
  dossierCode: string;
  dossierTitle: string;
  status: string;
  paymentStatus: string | null;
  startAt: string;
  endAt: string;
  expiresAt: string | null;
}

export interface AdvertisingAdminPlacementInventory
  extends AdvertisingPlacement {
  bookings: AdvertisingAdminInventoryItem[];
  reservations: AdvertisingAdminInventoryItem[];
}

export interface AdvertisingCampaignDistribution {
  campaignId: string;
  title: string | null;
  deliveryCount: number;
  validImpressions: number;
  validClicks: number;
  targetShareBasisPoints: number;
  actualShareBasisPoints: number;
}

export interface AdvertisingPlacementReport {
  placementId: string;
  placementCode: string;
  placementName: string;
  paidOrders: number;
  paidRevenueVnd: number;
  deliveryCount: number;
  validImpressions: number;
  validClicks: number;
  ctrBasisPoints: number;
  campaigns: AdvertisingCampaignDistribution[];
}
