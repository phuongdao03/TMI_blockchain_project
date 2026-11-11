export type FeeObligationStatus =
  | "OPEN"
  | "OVERDUE"
  | "PAID"
  | "WAIVED"
  | "CANCELLED";

export interface FeeObligation {
  id: string;
  dossierId: string;
  serviceCode: string;
  description: string;
  amountMinor: number;
  currency: string;
  taxMode: string;
  status: FeeObligationStatus;
  dueAt: string;
  paidAt: string | null;
}

export type FeePolicyStatus =
  | "DRAFT"
  | "SCHEDULED"
  | "ACTIVE"
  | "EXPIRED"
  | "CANCELLED";

export interface AdminFeePolicy {
  id: string;
  feeType: string;
  dossierTypeId: string;
  versionNo: number;
  amountMinor: number;
  currency: string;
  displayName: string;
  reason: string;
  startsAt: string;
  endsAt: string | null;
  status: FeePolicyStatus;
  createdByUserId: string;
  approvedByUserId: string | null;
  approvedAt: string | null;
}

export type FeeWaiverStatus =
  | "REQUESTED"
  | "APPROVED"
  | "REJECTED"
  | "REDEEMED"
  | "EXPIRED";

export interface AdminFeeWaiver {
  id: string;
  dossierId: string;
  feeType: string;
  amountMinor: number;
  currency: string;
  reason: string;
  status: FeeWaiverStatus;
  requestedByUserId: string;
  approvedByUserId: string | null;
  approvedAt: string | null;
  redeemedAt: string | null;
  expiresAt: string;
}
