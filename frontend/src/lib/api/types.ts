export interface ResponseMeta {
  request_id: string;
}

export interface ListResponseMeta {
  request_id?: string;
  requestId?: string;
  page: number;
  pageSize: number;
  total: number;
}

export type ActivityKind = "FAVORITE" | "SHARE";

export interface ActivityItem {
  activityId: string;
  kind: ActivityKind;
  publicWorkId: string;
  slug: string;
  title: string;
  shortDescription: string;
  channel: "NATIVE" | "COPY_LINK" | null;
  createdAt: string;
}

export interface ActivityPage {
  items: ActivityItem[];
  nextCursor: string | null;
}

export interface SuccessEnvelope<Data> {
  success: true;
  data: Data;
  meta: ResponseMeta;
}

export interface ErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}

export interface AuthUser {
  id: string;
  email: string;
  roles: string[];
  accountType: AccountType | null;
}

export type StaffAccountRole = "MODERATOR";
export type StaffAccountStatus =
  | "PENDING_MFA"
  | "ACTIVE"
  | "SUSPENDED"
  | "DISABLED";

export interface StaffAccount {
  id: string;
  email: string;
  role: string;
  status: StaffAccountStatus;
  createdAt: string | null;
  lastLoginAt: string | null;
}

export interface PrivilegedAction {
  id: string;
  targetUserId: string;
  action: "ROLE_CHANGE" | "MFA_RECOVERY";
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
  requestedRole: StaffAccountRole | "SUPER_ADMIN" | null;
  requestedByUserId: string;
  approvedByUserId: string | null;
  reason: string;
  expiresAt: string;
  resolvedAt: string | null;
}

export type StaffInvitationStatus =
  | "PENDING"
  | "ACCEPTED"
  | "REVOKED"
  | "EXPIRED";

export interface StaffInvitation {
  id: string;
  email: string;
  role: StaffAccountRole;
  organizationId: string | null;
  status: StaffInvitationStatus;
  expiresAt: string;
  createdAt: string | null;
}

export type AccountType =
  | "PUBLIC_USER"
  | "INDIVIDUAL_APPLICANT"
  | "ORGANIZATION_APPLICANT";

export interface CmsPost {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  bodyHtml: string;
  categoryId: string | null;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CmsPostInput {
  title: string;
  slug: string;
  excerpt?: string | null;
  bodyHtml: string;
  categoryId?: string | null;
}

export interface CmsPage {
  id: string;
  title: string;
  slug: string;
  bodyHtml: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
}

export interface CmsBanner {
  id: string;
  title: string;
  slug: string;
  imageUrl: string;
  linkUrl: string | null;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
}

export interface CmsCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

export interface OperationsMetrics {
  dossierFunnel: Record<string, number>;
  overdueReviews: number;
  reviewerWorkload: Array<{
    reviewerEmail: string;
    activeAssignments: number;
  }>;
  paymentFailures: number;
  blockchainFailures: number;
  publicCatalogCacheHitRatio: number;
  publicCatalogCacheOperations: Record<string, number>;
  jobStatusCounts: Record<string, number>;
  oldestQueuedJobAgeSeconds: number;
  jobRetryFailures: number;
  deadLetteredJobsByTask: Record<string, number>;
}

export type DurableJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "DEAD_LETTERED"
  | "CANCELLED";

export interface DurableJobSummary {
  id: string;
  taskName: string;
  queueName: string;
  resourceType: string;
  resourceId: string;
  status: DurableJobStatus;
  totalAttempts: number;
  maxAttempts: number;
  replayCount: number;
  version: number;
  scheduledAt: string;
  lastErrorCode: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface JobActionInput {
  expectedVersion: number;
  reason: string;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  readAt: string | null;
  createdAt: string;
}

export type VoteStatus =
  | "VALID"
  | "SUSPICIOUS"
  | "REVOKED_BY_USER"
  | "INVALIDATED"
  | "REJECTED";

export interface VoteHistoryItem {
  voteId: string;
  campaignId: string;
  campaignName: string;
  campaignSlug: string;
  workId: string;
  workTitle: string;
  workSlug: string;
  status: VoteStatus;
  createdAt: string;
  revokedAt: string | null;
  canChange: boolean;
  canRevoke: boolean;
}

export interface PublicVotingCampaign {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: VotingCampaignStatus;
  timezone: string;
  startAt: string;
  endAt: string;
  maxVotesPerUser: number;
  allowVoteChange: boolean;
  allowVoteRevoke: boolean;
  ruleVersion: number;
  serverTime: string;
}

export interface PublicCampaignWork {
  workId: string;
  title: string;
  slug: string;
  shortDescription: string;
}

export interface PublicVoteSummary {
  workId: string;
  workTitle: string;
  workSlug: string;
  effectiveCount: number;
  refreshedAt: string;
}

export interface PublicRankingSnapshot {
  id: string;
  campaignId: string;
  version: number;
  formulaVersion: string;
  campaignRuleVersion: number;
  sourceDigest: string;
  resultDigest: string;
  candidateCount: number;
  totalValidVotes: number;
  createdAt: string;
}

export interface PublicRankingItem {
  workId: string;
  slug: string;
  title: string;
  shortDescription: string;
  authorDisplayName: string | null;
  categoryId: string;
  categoryName: string;
  categorySlug: string | null;
  rank: number;
  categoryRank: number;
  displayOrder: number;
  score: number;
  effectiveVoteCount: number;
}

export interface PublicRankingData {
  snapshot: PublicRankingSnapshot;
  items: PublicRankingItem[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
}

export interface VotingEligibility {
  canVote: boolean;
  reasons: string[];
  remainingQuota: number;
  ruleVersion: number;
  serverTime: string;
}

export interface VoteMutationResult {
  voteId: string;
  campaignId: string;
  workId: string;
  status: VoteStatus;
  remainingQuota: number;
  ruleVersion: number;
  createdAt: string;
  previousVoteId: string | null;
}

export interface AuditLogItem {
  id: string;
  actorUserId: string | null;
  actorType: "USER" | "SERVICE" | "ANONYMOUS";
  actorService: string | null;
  action: string;
  resourceType: string;
  resourceId: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  requestId: string | null;
  integrityStatus: "VERIFIED" | "TAMPERED" | "UNSEALED" | "KEY_UNAVAILABLE";
  retentionUntil: string | null;
  createdAt: string;
}

export interface AuditIntegrityCheck {
  scanned: number;
  total: number;
  isComplete: boolean;
  counts: Record<AuditLogItem["integrityStatus"], number>;
}

export interface AuditListFilters {
  page?: number;
  pageSize?: number;
  actorUserId?: string;
  action?: string;
  resourceType?: string;
  createdFrom?: string;
  createdTo?: string;
}

export interface LoginData {
  user: AuthUser;
}

export interface MessageData {
  message: string;
}

export interface StatusData {
  status: string;
}

export interface UserProfile {
  userId: string;
  email: string;
  fullName: string | null;
  phone: string | null;
  avatarMediaId: string | null;
  locale: string;
  timezone: string;
}

export interface ProfileUpdate {
  fullName: string | null;
  phone: string | null;
  locale: string;
  timezone: string;
}

export interface ProfileAvatarUpdate {
  avatarMediaId: string;
}

export type MediaPurpose = "AVATAR" | "DOSSIER_EVIDENCE" | "PUBLIC_WORK";
export type MediaConfidentiality = "PRIVATE" | "PUBLIC";
export type MediaStatus =
  | "PENDING"
  | "ACTIVE"
  | "QUARANTINED"
  | "REJECTED"
  | "DELETED";

export interface MediaUploadIntent {
  confidentiality: MediaConfidentiality;
  purpose: MediaPurpose;
  filename: string;
  mimeType: string;
  size: number;
}

export interface MediaUploadAuthorization {
  mediaId: string;
  publicId: string;
  uploadUrl: string;
  cloudName: string;
  apiKey: string;
  signature: string;
  parameters: Record<string, string>;
  expiresAt: number;
}

export interface MediaUploadCompletion {
  mediaId: string;
  publicId: string;
  version: number;
  signature: string;
}

export interface MediaAsset {
  id: string;
  status: MediaStatus;
  mimeType: string;
  bytes: number;
  width: number | null;
  height: number | null;
  durationMs: number | null;
  inspectionAttempts?: number;
  inspectionReasonCode?: string | null;
  inspectedAt?: string | null;
}

export interface SignedDelivery {
  url: string;
  expiresAt: number;
}

export type OrganizationStatus = "ACTIVE" | "ARCHIVED";
export type MembershipRole = "OWNER" | "ORG_MANAGER" | "MEMBER";
export type MembershipStatus = "INVITED" | "ACTIVE";

export interface Organization {
  id: string;
  code: string;
  legalName: string;
  displayName: string;
  taxCode: string | null;
  status: OrganizationStatus;
  ownerUserId: string;
  currentRole: MembershipRole;
  canManageMembers: boolean;
}

export interface OrganizationMember {
  userId: string;
  email: string;
  roleCode: MembershipRole;
  status: MembershipStatus;
  joinedAt: string | null;
}

export interface OrganizationInput {
  code: string;
  legalName: string;
  displayName: string;
  taxCode: string | null;
}

export interface MemberInput {
  email: string;
  roleCode: Exclude<MembershipRole, "OWNER">;
  status: MembershipStatus;
}

export type DossierStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "PRECHECK"
  | "NEEDS_SUPPLEMENT"
  | "UNDER_REVIEW"
  | "COUNCIL_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "PAYMENT_PENDING"
  | "PAID"
  | "ANCHOR_PENDING"
  | "ANCHORED"
  | "CERTIFICATE_ISSUED"
  | "PUBLISHED"
  | "REVOKED"
  | "CANCELLED";

export type DossierVisibility = "PRIVATE" | "UNLISTED" | "PUBLIC";
export type EvidenceAccessScope =
  | "PRIVATE"
  | "INTERNAL"
  | "PUBLIC_PREVIEW"
  | "PUBLIC";

export interface Dossier {
  id: string;
  code: string;
  ownerUserId: string;
  organizationId: string | null;
  categoryId: string;
  dossierTypeId: string | null;
  dossierTypeVersionId: string | null;
  formData: Record<string, unknown>;
  title: string;
  slug: string | null;
  summary: string | null;
  status: DossierStatus;
  visibility: DossierVisibility;
  currentVersionNo: number;
  submittedAt: string | null;
  createdAt: string;
  updatedAt: string;
  canEdit: boolean;
}

export interface DossierEvidence {
  id: string;
  dossierId: string;
  dossierVersionId: string | null;
  mediaAssetId: string;
  evidenceType: string;
  evidenceRole: string | null;
  accessScope: EvidenceAccessScope;
  title: string;
  description: string | null;
  issuedAt: string | null;
  displayOrder: number;
  isPublic: boolean;
  mimeType: string;
  bytes: number;
  sha256: string;
}

export interface DossierDocumentRule {
  key: string;
  label: string;
  documentType: string;
  required: boolean;
  allowedMimeTypes: string[];
  maxBytes: number;
  maxCount: number;
  defaultVisibility: EvidenceAccessScope;
}

export interface DossierDetail extends Dossier {
  evidences: DossierEvidence[];
  documentRules: DossierDocumentRule[];
}

export interface DossierInput {
  categoryId: string;
  organizationId?: string | null;
  title: string;
  slug?: string | null;
  summary?: string | null;
  visibility: DossierVisibility;
  dossierTypeVersionId?: string | null;
  formData?: Record<string, unknown> | null;
}

export interface DossierTypeField {
  key: string;
  type:
    | "text"
    | "textarea"
    | "number"
    | "date"
    | "datetime"
    | "select"
    | "multiselect"
    | "radio"
    | "checkbox"
    | "currency"
    | "email"
    | "phone"
    | "address"
    | "person"
    | "organization"
    | "file";
  label?: string;
  helpText?: string;
  placeholder?: string;
  required?: boolean;
  options?: Array<string | { value: string; label?: string }>;
}

export interface DossierTypeDefinition {
  description?: string;
  fields: DossierTypeField[];
  documentRules?: Array<{
    key: string;
    label?: string;
    documentType: string;
    required?: boolean;
    allowedMimeTypes: string[];
    maxBytes: number;
    maxCount?: number;
    defaultVisibility?: EvidenceAccessScope;
  }>;
  requirements?: Array<{
    key: string;
    label?: string;
    required?: boolean;
    fileRoles: string[];
  }>;
  reviewChecklist?: Array<{ key: string; label?: string; required?: boolean }>;
}

export interface DossierTypeVersion {
  id: string;
  dossierTypeId: string;
  versionNo: number;
  schema: DossierTypeDefinition;
}

export interface DossierType {
  id: string;
  categoryId: string;
  code: string;
  name: string;
  isActive: boolean;
  currentVersion: DossierTypeVersion;
}

export type DossierPatch = Partial<
  Pick<
    DossierInput,
    | "categoryId"
    | "organizationId"
    | "title"
    | "slug"
    | "summary"
    | "visibility"
  >
>;

export interface EvidenceInput {
  mediaAssetId: string;
  evidenceType: string;
  evidenceRole?: string | null;
  title: string;
  description?: string | null;
  issuedAt?: string | null;
  displayOrder?: number;
  isPublic?: boolean;
}

export interface DossierVersion {
  id: string;
  dossierId: string;
  versionNo: number;
  snapshotJson: Record<string, unknown>;
  canonicalHash: string;
  submittedBy: string;
  submittedAt: string;
}

export interface DossierTimelineItem {
  id: string;
  dossierId: string;
  fromStatus: DossierStatus;
  toStatus: DossierStatus;
  actorUserId: string;
  reasonCode: string | null;
  note: string | null;
  createdAt: string;
}

export interface DossierSubmission {
  dossier: Dossier;
  version: DossierVersion;
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
}

export interface DossierListFilters {
  categoryId?: string;
  page?: number;
  pageSize?: number;
  status?: DossierStatus;
}

export type ReviewAssignmentStatus =
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "CONFLICTED"
  | "SUBMITTED"
  | "CANCELLED";

export type ReviewRecommendation = "APPROVE" | "SUPPLEMENT" | "REJECT";
export type ReviewFindingSeverity =
  | "INFO"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";
export type ReviewFindingAction = "NOTE" | "SUPPLEMENT" | "ESCALATE";

export interface ReviewFinding {
  id: string;
  severity: ReviewFindingSeverity;
  criterion:
    | "truth"
    | "transparency"
    | "ownership"
    | "professionalism"
    | "respect";
  evidenceMediaIds: string[];
  title: string;
  description: string;
  action: ReviewFindingAction;
}

export interface ReviewAssignment {
  id: string;
  dossierId: string;
  dossierVersionId: string;
  reviewerUserId: string;
  assignedBy: string;
  dueAt: string | null;
  status: ReviewAssignmentStatus;
  conflictDeclaredAt: string | null;
  conflictReason: string | null;
}

export interface ReviewAssignmentSummary {
  assignment: ReviewAssignment;
  dossierCode: string;
  dossierTitle: string;
  versionNo: number;
}

export interface ReviewEvidenceSnapshot {
  id: string;
  mediaAssetId: string;
  evidenceType: string;
  title: string;
  description: string | null;
  issuedAt: string | null;
  displayOrder: number;
  isPublic: boolean;
  media: {
    mimeType: string;
    bytes: number;
    sha256: string;
  };
}

export interface ReviewSnapshot {
  schemaVersion: number;
  dossier: {
    id: string;
    code: string;
    title: string;
    summary?: string | null;
  };
  evidences: ReviewEvidenceSnapshot[];
}

export interface ReviewDraft {
  truthScore: number | null;
  transparencyScore: number | null;
  ownershipScore: number | null;
  professionalismScore: number | null;
  respectScore: number | null;
  criterionComments: Record<string, string>;
  criterionEvidence: Record<string, string[]>;
  findings: ReviewFinding[];
  checklistAnswers: Record<string, boolean>;
  applicantFeedback: string | null;
  recommendation: ReviewRecommendation | null;
  privateNote: string | null;
}

export interface ReviewData extends ReviewDraft {
  id: string;
  assignmentId: string;
  totalScore: number | null;
  submittedAt: string | null;
}

export interface ReviewAssignmentDetail extends ReviewAssignmentSummary {
  canonicalHash: string | null;
  snapshotJson: ReviewSnapshot | null;
  review: ReviewData | null;
}

export interface ReviewListFilters {
  page?: number;
  pageSize?: number;
  status?: ReviewAssignmentStatus;
}

export type SimilarityCaseStatus = "OPEN" | "ASSIGNED" | "RESOLVED";
export type SimilaritySignalType = "TEXT" | "IMAGE";
export type SimilarityCaseDisposition = "DISTINCT" | "RELATED" | "SAME_WORK";

export interface SimilarityAssetSummary {
  dossierId: string;
  dossierCode: string;
  dossierTitle: string;
  versionNo: number;
  evidenceMediaIds: string[];
}

export interface SimilarityCase {
  id: string;
  leftDossierVersionId: string;
  rightDossierVersionId: string;
  leftAsset: SimilarityAssetSummary | null;
  rightAsset: SimilarityAssetSummary | null;
  signalType: SimilaritySignalType;
  textScore: number | null;
  imageDistance: number | null;
  policyVersion: string;
  status: SimilarityCaseStatus;
  assignedReviewerUserId: string | null;
  disposition: SimilarityCaseDisposition | null;
  resolutionReason: string | null;
  createdAt: string;
  assignedAt: string | null;
  resolvedAt: string | null;
}

export interface SimilarityCaseFilters {
  page?: number;
  pageSize?: number;
  status?: SimilarityCaseStatus;
}

export type CouncilSessionStatus = "DRAFT" | "OPEN" | "CLOSED";

export type CouncilVoteChoice =
  | "APPROVE"
  | "REJECT"
  | "ABSTAIN"
  | "REQUEST_MORE_INFO";

export type CouncilCaseDecision = Exclude<CouncilVoteChoice, "ABSTAIN">;

export interface CouncilSession {
  id: string;
  code: string;
  title: string;
  scheduledAt: string;
  status: CouncilSessionStatus;
  quorumRequired: number;
  openedAt: string | null;
  closedAt: string | null;
  minutesHash: string | null;
  memberCount: number;
  attendanceCount: number;
}

export interface CouncilMember {
  id: string;
  sessionId: string;
  memberUserId: string;
  attendanceConfirmedAt: string | null;
}

export interface CouncilCase {
  id: string;
  sessionId: string;
  dossierId: string;
  dossierVersionId: string;
  dossierCode: string;
  dossierTitle: string;
  versionNo: number;
  decision: CouncilCaseDecision | null;
}

export interface CouncilConflict {
  id: string;
  caseId: string;
  memberUserId: string;
  hasConflict: boolean;
  reason: string | null;
  declaredAt: string;
}

export interface CouncilVote {
  id: string;
  caseId: string;
  memberUserId: string;
  choice: CouncilVoteChoice;
  reason: string;
  votedAt: string;
}

export interface CouncilCaseResult {
  caseId: string;
  dossierId: string;
  dossierVersionId: string;
  decision: CouncilCaseDecision | null;
  quorumMet: boolean;
  validVoteCount: number;
  voteCounts: Record<CouncilVoteChoice, number>;
}

export interface CouncilSessionListItem {
  session: CouncilSession;
  myAttendanceConfirmedAt: string | null;
}

export interface CouncilCaseDetail {
  case: CouncilCase;
  myConflict: CouncilConflict | null;
  myVote: CouncilVote | null;
  result: CouncilCaseResult | null;
}

export interface CouncilSessionDetail {
  session: CouncilSession;
  myAttendanceConfirmedAt: string | null;
  cases: CouncilCaseDetail[];
}

export interface CouncilMinutes {
  sessionId: string;
  sessionCode: string;
  closedAt: string;
  quorumRequired: number;
  minutesHash: string;
  cases: CouncilCaseResult[];
}

export interface CouncilListFilters {
  page?: number;
  pageSize?: number;
  status?: CouncilSessionStatus;
}

export type CertificateStatus = "ACTIVE" | "EXPIRED" | "REVOKED";
export type BlockchainTransactionStatus =
  | "CREATED"
  | "SIGNING"
  | "BROADCAST"
  | "CONFIRMED"
  | "FAILED"
  | "REPLACED";

export type BlockchainWalletLinkStatus = "ACTIVE" | "REVOKED";
export type BlockchainIntentStatus =
  | "PREPARED"
  | "SUBMITTED"
  | "EXPIRED"
  | "CANCELLED";

export interface BlockchainWalletChallenge {
  id: string;
  message: string;
  nonce: string;
  expiresAt: string;
}

export interface BlockchainWalletLink {
  id: string;
  walletAddress: string;
  chainId: number;
  status: BlockchainWalletLinkStatus;
  verifiedAt: string;
}

export interface BlockchainSigningQueueItem {
  transactionId: string;
  dossierId: string;
  dossierCode: string;
  dossierTitle: string;
  dossierVersionNo: number;
  certificateNumber: string | null;
  proofHash: string;
  status: BlockchainTransactionStatus;
  txHash: string | null;
  errorCode: string | null;
  createdAt: string;
}

export interface BlockchainSigningContext {
  transactionId: string;
  dossierId: string;
  dossierCode: string;
  dossierTitle: string;
  dossierVersionNo: number;
  certificateNumber: string | null;
  method: string;
  proofHash: string;
  network: string;
  chainId: number;
  contractAddress: string;
  status: BlockchainTransactionStatus;
}

export interface BlockchainSigningIntent {
  id: string;
  transactionId: string;
  transactionRequest: Record<string, string>;
  expiresAt: string;
  estimatedGas: number;
  gasPriceWei: number;
  walletBalanceWei: number;
}

export interface BlockchainSigningStatus {
  transactionId: string;
  status: BlockchainTransactionStatus;
  txHash: string | null;
  confirmations: number;
  errorCode: string | null;
  errorMessage: string | null;
  confirmedAt: string | null;
}

export interface Certificate {
  id: string;
  certificateNumber: string;
  dossierId: string;
  dossierCode: string;
  assetTitle: string;
  categoryName: string;
  currentVersionNo: number;
  status: CertificateStatus;
  issuedAt: string;
  expiresAt: string | null;
  pdfReady: boolean;
  network: string | null;
  contractAddress: string | null;
  transactionHash: string | null;
  blockchainStatus: BlockchainTransactionStatus | null;
  confirmations: number;
}

export interface CertificateDetail {
  certificate: Certificate;
  metadata: Record<string, unknown>;
  metadataHash: string;
  qrPayload: string;
}

export interface CertificateDownload {
  url: string;
  expiresAt: number;
}

export type CertificateVersionStatus =
  | "PENDING_APPROVAL"
  | "REJECTED"
  | "ANCHOR_PENDING"
  | "FAILED"
  | "ACTIVE"
  | "SUPERSEDED"
  | "REVOKED";

export interface CertificateVersion {
  id: string;
  certificateId: string;
  versionNo: number;
  dossierVersionId: string;
  predecessorVersionId: string | null;
  status: CertificateVersionStatus;
  changeReason: string | null;
  requestedBy: string | null;
  requestedAt: string | null;
  decidedBy: string | null;
  decidedAt: string | null;
  rejectionReason: string | null;
  metadataHash: string;
  blockchainTransactionId: string | null;
  pdfReady: boolean;
  createdAt: string;
}

export interface PublicCategory {
  id: string;
  code: string;
  name: string;
  slug: string | null;
  description: string | null;
  assetCount: number;
}

export interface PublicAsset {
  slug: string;
  title: string;
  summary: string | null;
  categoryCode: string;
  categoryName: string;
  certificateNumber: string;
  certificateStatus: CertificateStatus;
  issuedAt: string;
  transactionHash: string | null;
}

export interface PublicAssetDetail {
  asset: PublicAsset;
  metadata: Record<string, unknown>;
  network: string | null;
  contractAddress: string | null;
  confirmations: number;
}

export interface PublicMapMarker {
  slug: string;
  title: string;
  categoryName: string;
  latitude: number;
  longitude: number;
}

export type VerificationStatus =
  | "VALID"
  | "MISMATCH"
  | "REVOKED"
  | "EXPIRED"
  | "PENDING"
  | "NOT_FOUND";

export interface Verification {
  status: VerificationStatus;
  checkedAt: string;
  certificateNumber: string | null;
  assetTitle: string | null;
  categoryName: string | null;
  issuedAt: string | null;
  expiresAt: string | null;
  version: number | null;
  network: string | null;
  contractAddress: string | null;
  transactionHash: string | null;
  confirmations: number;
  confirmedAt: string | null;
  explorerUrl: string | null;
  dossierCode?: string | null;
  metadataHash?: string | null;
  blockNumber?: number | null;
  issuerLabel?: string | null;
  documents?: PublicEvidenceProof[];
}

export interface PublicEvidenceProof {
  title: string;
  evidenceType: string;
  sha256: string;
}

export type DocumentVerificationStatus =
  | "MATCH"
  | "NO_MATCH"
  | "PENDING_CONFIRMATION"
  | "CHAIN_UNAVAILABLE"
  | "NOT_FOUND"
  | "NOT_AUTHORIZED";

export interface DocumentVerification {
  status: DocumentVerificationStatus;
  checkedAt: string;
}

export interface PublicCertificateVersion {
  versionNo: number;
  status: "ACTIVE" | "SUPERSEDED" | "REVOKED";
  metadataHash: string;
  transactionHash: string | null;
  blockNumber: number | null;
  confirmedAt: string | null;
  createdAt: string;
  issuerLabel: string;
  documents: PublicEvidenceProof[];
}

export type PublicationStatus =
  | "DRAFT"
  | "PENDING_PUBLICATION"
  | "PUBLISHED"
  | "HIDDEN"
  | "SUSPENDED"
  | "ARCHIVED";
export type PublicWorkVisibility = "PRIVATE" | "UNLISTED" | "PUBLIC";
export type PublicMediaKind = "IMAGE" | "AUDIO" | "VIDEO" | "DOCUMENT";
export type DerivativeStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export interface PublicationChecklistItem {
  code: string;
  passed: boolean;
}

export interface PublicWorkAdmin {
  id: string;
  dossierId: string;
  certificateId: string | null;
  slug: string;
  title: string;
  shortDescription: string;
  publicationStatus: PublicationStatus;
  visibility: PublicWorkVisibility;
  publishedAt: string | null;
  scheduledPublishAt: string | null;
  featuredAt: string | null;
  featuredUntil: string | null;
  version: number;
}

export interface PublicWorkEditor extends PublicWorkAdmin {
  fullDescription: string | null;
  authorDisplayName: string | null;
  categoryId: string;
  categoryName: string;
  tagIds: string[];
  thumbnailMediaId: string | null;
  checklist: PublicationChecklistItem[];
}

export interface PublicWorkEditorInput {
  expectedVersion: number;
  slug: string;
  title: string;
  shortDescription: string;
  fullDescription: string | null;
  authorDisplayName: string | null;
  categoryId: string;
  tagIds: string[];
  visibility: PublicWorkVisibility;
  thumbnailMediaId: string | null;
}

export interface PublicWorkCategory {
  id: string;
  parentId: string | null;
  code: string;
  name: string;
  slug: string | null;
  description: string | null;
  isActive: boolean;
  displayOrder: number;
}

export interface PublicWorkTag {
  id: string;
  name: string;
  slug: string;
  isActive: boolean;
}

export interface PublicWorkMedia {
  id: string;
  mediaAssetId: string;
  mediaKind: PublicMediaKind;
  sortOrder: number;
  caption: string | null;
  altText: string | null;
  derivativeStatus: DerivativeStatus;
  derivativeMimeType: string | null;
  derivativeWidth: number | null;
  derivativeHeight: number | null;
  durationMs: number | null;
  attemptCount: number;
  failureCode: string | null;
}

export interface PublicWorkPreviewMedia {
  id: string;
  kind: PublicMediaKind;
  sortOrder: number;
  caption: string | null;
  altText: string | null;
  url: string | null;
  mimeType: string | null;
  width: number | null;
  height: number | null;
  durationMs: number | null;
  isThumbnail: boolean;
}

export interface PublicWorkPreview {
  slug: string;
  title: string;
  shortDescription: string;
  fullDescription: string | null;
  authorDisplayName: string | null;
  categoryName: string;
  media: PublicWorkPreviewMedia[];
  canPublish: boolean;
}

export type PublicWorkSort = "newest" | "featured" | "popular";

export interface PublicCatalogTag {
  name: string;
  slug: string;
}

export interface PublicCatalogWork {
  id: string;
  slug: string;
  title: string;
  shortDescription: string;
  authorDisplayName: string | null;
  categoryName: string;
  categorySlug: string;
  tags: PublicCatalogTag[];
  publishedAt: string;
  isFeatured: boolean;
  thumbnailUrl: string | null;
  thumbnailAltText: string | null;
}

export interface PublicCatalogFilters {
  query?: string;
  category?: string;
  tag?: string;
  publishedFrom?: string;
  publishedTo?: string;
  sort?: PublicWorkSort;
  page?: number;
  pageSize?: number;
}

export interface PublicCatalogPage {
  success: true;
  data: PublicCatalogWork[];
  meta: ListResponseMeta;
}

export interface PublicCatalogInitialData {
  featured?: PublicCatalogWork[];
  works?: PublicCatalogPage;
}

export type SearchAutocompleteKind = "work" | "category" | "tag";

export interface SearchAutocompleteSuggestion {
  kind: SearchAutocompleteKind;
  label: string;
  slug: string;
}

export type SearchSort = "relevance" | "newest" | "oldest" | "most_viewed";
export type SearchTagMode = "any" | "all";

export interface SearchParameters {
  q?: string;
  category?: string;
  tags: string[];
  tagsMode: SearchTagMode;
  organization?: string;
  publishedFrom?: string;
  publishedTo?: string;
  hasBlockchainProof?: boolean;
  certificateStatus?: CertificateStatus;
  sort: SearchSort;
  cursor?: string;
}

export interface SearchResultWork {
  id: string;
  slug: string;
  title: string;
  shortDescription: string;
  authorDisplayName: string | null;
  categoryName: string;
  categorySlug: string;
  certificateNumber: string | null;
  certificateStatus: CertificateStatus | null;
  publishedAt: string;
}

export interface SearchResponse {
  success: true;
  data: SearchResultWork[];
  meta: {
    requestId: string;
    nextCursor: string | null;
    durationMs: number;
    version: string;
  };
}

export interface SearchFacetValue {
  slug: string;
  label: string;
  count: number;
}

export interface SearchFacets {
  categories: SearchFacetValue[];
  tags: SearchFacetValue[];
  approximate: boolean;
}

export interface SearchHistoryItem {
  id: string;
  displayQuery: string;
  searchedAt: string;
}

export interface SearchHistoryState {
  isEnabled: boolean;
  items: SearchHistoryItem[];
}

export interface SearchHistoryRecorded {
  recorded: boolean;
}

export interface SearchTrendingItem {
  queryHash: string;
  query: string;
  searchCount: number;
}

export interface SearchRelatedWork {
  id: string;
  slug: string;
  title: string;
  shortDescription: string;
  categoryName: string;
  categorySlug: string;
  publishedAt: string;
}

export interface SearchAnalyticsPoint {
  periodStart: string;
  categorySlug: string | null;
  searchCount: number;
  zeroResultCount: number;
  clickCount: number;
  latencyP95Ms: number;
}

export interface SearchAnalytics {
  searchCount: number;
  zeroResultCount: number;
  clickCount: number;
  clickThroughRate: number;
  zeroResultRate: number;
  latencyP95Ms: number;
  points: SearchAnalyticsPoint[];
  privacyMode: "aggregate-only";
}

export interface PublicCertificateSummary {
  certificateNumber: string;
  status: CertificateStatus;
  issuedAt: string;
  expiresAt: string | null;
}

export interface PublicProofSummary {
  network: string;
  transactionHash: string | null;
  status: BlockchainTransactionStatus;
  confirmations: number;
  confirmedAt: string | null;
}

export interface PublicWorkDetailMedia {
  id: string;
  kind: PublicMediaKind;
  sortOrder: number;
  caption: string | null;
  altText: string | null;
  url: string | null;
  mimeType: string | null;
  width: number | null;
  height: number | null;
  durationMs: number | null;
  isThumbnail: boolean;
}

export interface PublicWorkDetail {
  id: string;
  slug: string;
  title: string;
  shortDescription: string;
  fullDescription: string | null;
  authorDisplayName: string | null;
  organizationDisplayName: string | null;
  categoryName: string;
  categorySlug: string;
  tags: PublicCatalogTag[];
  publishedAt: string;
  visibility: PublicWorkVisibility;
  certificate: PublicCertificateSummary | null;
  proof: PublicProofSummary | null;
  media: PublicWorkDetailMedia[];
  relatedWorks: PublicCatalogWork[];
  canonicalSlug: string;
  redirected: boolean;
}

export type ContentReportReason =
  | "COPYRIGHT"
  | "INCORRECT_INFORMATION"
  | "INAPPROPRIATE_CONTENT"
  | "OTHER";

export type ContentReportStatus =
  | "OPEN"
  | "UNDER_REVIEW"
  | "RESOLVED"
  | "DISMISSED"
  | "SUSPENDED";

export interface ContentReportAccepted {
  id: string;
  status: ContentReportStatus;
}

export interface ContentReportAdmin {
  id: string;
  publicWorkId: string;
  workTitle: string;
  workSlug: string;
  workVersion: number;
  reason: ContentReportReason;
  description: string | null;
  status: ContentReportStatus;
  reporterType: "USER" | "ANONYMOUS";
  hasContactEmail: boolean;
  assignedToUserId: string | null;
  resolutionNote: string | null;
  resolvedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export type VotingCampaignStatus =
  | "DRAFT"
  | "SCHEDULED"
  | "ACTIVE"
  | "PAUSED"
  | "ENDED"
  | "RESULT_PENDING"
  | "PUBLISHED"
  | "CANCELLED";

export interface VotingCampaign {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: VotingCampaignStatus;
  campaignType: "PERIODIC" | "SPECIAL";
  periodType: "WEEKLY" | "MONTHLY" | "QUARTERLY" | "YEARLY" | "CUSTOM";
  timezone: string;
  startAt: string;
  endAt: string;
  maxVotesPerUser: number;
  maxVotesPerWorkPerUser: number;
  allowVoteChange: boolean;
  allowVoteRevoke: boolean;
  requireVerifiedEmail: boolean;
  minAccountAgeHours: number;
  eligibilityRules: { organizationIds: string[]; allowedRoles: string[] };
  ruleVersion: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export type CampaignParticipantStatus = "PENDING" | "APPROVED" | "REMOVED";

export interface CampaignParticipant {
  id: string;
  campaignId: string;
  workId: string;
  status: CampaignParticipantStatus;
  title: string;
  slug: string;
  approvedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
