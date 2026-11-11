export interface WalletTopup {
  id: string;
  orderCode: string;
  amountMinor: number;
  status: string;
  checkoutUrl: string | null;
  qrPayload?: string | null;
  bankBin?: string | null;
  bankAccountNumber?: string | null;
  bankAccountName?: string | null;
  transferDescription?: string | null;
  createdAt: string;
  expiresAt: string;
  paidAt: string | null;
}

export interface WalletBank {
  bankBin: string;
  bankName: string;
}

export interface WalletBankAccount {
  id: string;
  bankBin: string;
  bankName: string;
  accountNumberMasked: string;
  accountName: string;
  verificationStatus: string;
  isDefault: boolean;
  isActive: boolean;
}

export type WalletWithdrawalStatus =
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"
  | "QUEUED"
  | "PROCESSING"
  | "RECONCILIATION_REQUIRED"
  | "SUCCEEDED"
  | "FAILED"
  | "UNKNOWN";

export interface WalletWithdrawal {
  id: string;
  providerReference: string;
  bankNameSnapshot: string;
  accountNumberMasked: string;
  amountMinor: number;
  feeMinor: number;
  netAmountMinor: number;
  status: WalletWithdrawalStatus;
  createdAt: string;
  approvedAt: string | null;
  rejectedAt: string | null;
  succeededAt: string | null;
  rejectionReason: string | null;
}

export interface AdminWalletWithdrawal extends WalletWithdrawal {
  userId: string;
  bankBinSnapshot: string;
  accountNumber: string;
  accountName: string;
  approvals: Array<Record<string, unknown>>;
  events: Array<Record<string, unknown>>;
  payoutAttempts: PayoutAttempt[];
}

export interface PayoutAttempt {
  id: string;
  referenceId: string;
  providerPayoutId: string | null;
  status: string;
  providerErrorCode: string | null;
  responseRedacted: Record<string, unknown>;
  attemptCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface FinanceReconciliation {
  checkedJournals: number;
  unbalancedJournals: number;
  unbalancedJournalIds: string[];
  checkedReservedAccounts: number;
  reservedBalanceMismatches: Array<Record<string, unknown>>;
  payoutExceptions: Array<Record<string, unknown>>;
}

export interface FinancialIdentityReview {
  userId: string;
  status: "VERIFIED" | "REJECTED";
  checkedAt: string;
}

export interface WalletWithdrawalSettings {
  enabled: boolean;
  minimumAmountMinor: number;
  maximumAmountMinor: number;
  dailyLimitMinor: number;
  dailyCountLimit: number;
  feeMode: "NONE" | "FIXED" | "BPS";
  feeValue: number;
  manualApprovalRequired: boolean;
  twoPersonThresholdMinor: number | null;
  payoutLiveEnabled: boolean;
}

export interface FinanceSettingsUpdateInput {
  withdrawalEnabled: boolean;
  payoutLiveEnabled: boolean;
  minimumAmountMinor: number;
  maximumAmountMinor: number;
  dailyLimitMinor: number;
  dailyCountLimit: number;
  feeMode: "NONE" | "FIXED" | "BPS";
  feeValue: number;
  twoPersonThresholdMinor: number | null;
}

export interface WalletSummary {
  balanceMinor: number;
  currency: "VND";
  provider: string;
  transactions: {
    id: string;
    walletDelta: number;
    balanceAfter: number;
    kind: string;
    description: string;
    createdAt: string;
  }[];
  topups: WalletTopup[];
}
