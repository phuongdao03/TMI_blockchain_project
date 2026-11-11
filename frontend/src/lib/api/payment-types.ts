export interface PaymentCandidate {
  dossierId: string;
  dossierCode: string;
  dossierTitle: string;
  versionNo: number;
}

export type PaymentStatus =
  | "PENDING"
  | "PROCESSING"
  | "PAID"
  | "FAILED"
  | "CANCELLED"
  | "EXPIRED"
  | "REFUNDED";

export interface PaymentOrder {
  purpose?: string | null;
  id: string;
  orderCode: string;
  dossierId: string;
  provider: string;
  providerOrderId: string | null;
  amountMinor: number;
  currency: string;
  status: PaymentStatus;
  expiresAt: string;
  paidAt: string | null;
  checkoutUrl: string | null;
  qrPayload: string | null;
  createdAt: string;
  updatedAt: string;
  description?: string | null;
  dueAt?: string | null;
  issuedByUserId?: string | null;
  issuedAt?: string | null;
  bankBin?: string | null;
  bankAccountNumber?: string | null;
  bankAccountName?: string | null;
  transferDescription?: string | null;
}

export interface AdminPaymentOrder {
  order: PaymentOrder;
  dossierCode: string;
  dossierTitle: string;
}

export interface PaymentHistoryFilters {
  status?: PaymentStatus;
  createdFrom?: string;
  createdTo?: string;
  query?: string;
  page?: number;
  pageSize?: number;
}

export interface AdminPaymentHistoryRow {
  order: PaymentOrder;
  dossierCode: string;
  dossierTitle: string;
  applicantUserId: string;
  applicantEmail: string;
  initiatedByEmail: string | null;
}

export interface PaymentStatusHistoryItem {
  id: string;
  fromStatus: string | null;
  toStatus: string;
  source: string;
  actorUserId: string | null;
  actorEmail: string | null;
  changedAt: string;
}

export interface AdminPaymentHistorySummary {
  total: number;
  statusCounts: Partial<Record<PaymentStatus, number>>;
  totalAmountMinor: number;
  paidAmountMinor: number;
}

export interface AdminPaymentHistoryPage {
  rows: AdminPaymentHistoryRow[];
  summary: AdminPaymentHistorySummary;
}

export interface AdminPaymentHistoryDetail {
  row: AdminPaymentHistoryRow;
  statusHistory: PaymentStatusHistoryItem[];
}
