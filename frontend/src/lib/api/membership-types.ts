export type MembershipTier = "MEMBER" | "SILVER" | "COMPANION" | "PRESTIGE";

export interface MembershipPlan {
  id: string;
  name: string;
  tier: Exclude<MembershipTier, "MEMBER">;
  amountMinor: number;
  durationDays: number;
  description: string;
  benefits: string[];
  conditions: string;
  active: boolean;
}
export interface MembershipPlanCatalog {
  plans: MembershipPlan[];
  member: {
    name: string;
    description: string;
    benefits: string[];
    conditions: string;
  };
}
export interface MembershipQuote {
  planId: string;
  name: string;
  tier: Exclude<MembershipTier, "MEMBER">;
  kind: "NEW" | "UPGRADE" | "RENEWAL";
  fromTier: MembershipTier;
  listPriceMinor: number;
  creditMinor: number;
  amountDueMinor: number;
  durationDays: number;
  remainingDays: number;
  expiresAt: string;
  approvalRequired: boolean;
}
export type DiamondApplicationStatus =
  | "PENDING"
  | "INFO_REQUESTED"
  | "APPROVED"
  | "REJECTED";
export interface DiamondApplication {
  id: string;
  userId: string;
  statement: string;
  status: DiamondApplicationStatus;
  decisionNote: string | null;
  reviewedByUserId: string | null;
  reviewedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
export type MembershipBenefitCode =
  | "COLLABORATION_NEED"
  | "ADVISORY_SESSION"
  | "FACILITATED_INTRODUCTION"
  | "MEMBER_STORY";
export type MembershipBenefitRequestStatus =
  | "PENDING"
  | "INFO_REQUESTED"
  | "APPROVED"
  | "COMPLETED"
  | "REJECTED";
export interface MembershipBenefitRequest {
  id: string;
  userId: string;
  benefit: MembershipBenefitCode;
  cycleStartedAt: string;
  statement: string;
  status: MembershipBenefitRequestStatus;
  decisionNote: string | null;
  reviewedByUserId: string | null;
  reviewedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
export interface MembershipBenefitRequestList {
  requests: MembershipBenefitRequest[];
}
export interface MembershipCollaborationNeed {
  id: string;
  displayName: string;
  username: string | null;
  statement: string;
  createdAt: string;
}
export interface MembershipCollaborationNeedList {
  requests: MembershipCollaborationNeed[];
}
export interface DiamondApplicationList {
  applications: DiamondApplication[];
}
export interface MembershipState {
  tier: MembershipTier;
  memberNumber: string;
  status: "ACTIVE" | "FREE";
  expiresAt: string | null;
}
export interface MembershipOverview extends MembershipState {
  plans: MembershipPlan[];
  purchases: {
    id: string;
    planId: string;
    tier: string;
    amountMinor: number;
    expiresAt: string;
    createdAt: string;
  }[];
}
