import type { SuccessEnvelope } from "./api-contract-types";
import type { MembershipTier } from "./membership-types";

export interface CommunityCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  sortOrder: number;
}

export interface CommunityAuthor {
  id: string;
  username: string;
  displayName: string | null;
  avatarUrl: string | null;
  roleLabel?: string | null;
  isAdmin?: boolean;
  membershipTier?: MembershipTier;
}

export interface CommunityCommentAuthor {
  id: string;
  username: string;
  displayName: string | null;
  avatarUrl: string | null;
  roleLabel?: string | null;
  isAdmin?: boolean;
  membershipTier?: MembershipTier;
}

export interface CommunityCommentFields {
  id: string;
  content: string;
  author: CommunityCommentAuthor | null;
  isDeleted: boolean;
  createdAt: string;
  likeCount: number;
  viewerHasLiked: boolean;
}

export interface CommunityCommentReply extends CommunityCommentFields {
  parentId: string;
}

export interface CommunityCommentThread extends CommunityCommentFields {
  parentId: null;
  replies: CommunityCommentReply[];
}

export interface CommunityCommentInput {
  content: string;
  parentId?: string;
}

export interface CommunityCommentCreateResult extends CommunityCommentFields {
  postId: string;
  parentId: string | null;
}

export type CommunityCommentSort = "oldest" | "newest";

export interface CommunityPostLikeResult {
  postId: string;
  likeCount: number;
  isLiked: boolean;
}

export interface CommunityCommentLikeResult {
  commentId: string;
  likeCount: number;
  isLiked: boolean;
}

export interface CommunityPostBookmarkResult {
  postId: string;
  isBookmarked: boolean;
}

export interface CommunityPostFollowResult {
  postId: string;
  isFollowing: boolean;
}

export interface CommunityMemberProfile {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string | null;
  roleLabel?: string | null;
  isAdmin?: boolean;
  membershipTier?: MembershipTier;
  bio: string | null;
  professionalTitle?: string | null;
  organization?: string | null;
  activityFields?: string | null;
  professionalLinks?: string[];
  joinedAt: string;
  publishedPostCount: number;
  followerCount: number;
  followingCount: number;
  viewerIsFollowing: boolean;
}

export interface CommunityMemberDirectoryItem {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string | null;
  membershipTier: MembershipTier;
  professionalTitle: string | null;
  organization: string | null;
  activityFields: string | null;
  professionalLinks: string[];
}

export interface CommunityMemberDirectoryPage {
  members: CommunityMemberDirectoryItem[];
  total: number;
}

export interface CommunityMemberFollowResult {
  memberId: string;
  isFollowing: boolean;
  followerCount: number;
}

export interface CommunityMemberCard {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string | null;
  roleLabel?: string | null;
  isAdmin?: boolean;
  membershipTier?: MembershipTier;
  viewerIsFollowing: boolean;
}

export interface CommunityProfileUpdateInput {
  username?: string;
  displayName?: string | null;
  avatarUrl?: string | null;
  avatarMediaId?: string | null;
  bio?: string | null;
  professionalTitle?: string | null;
  organization?: string | null;
  activityFields?: string | null;
  professionalLinks?: string[] | null;
}

export interface CommunityPostCategory {
  id: string;
  name: string;
  slug: string;
}

export interface CommunityRelatedWork {
  id: string;
  title: string;
  slug: string;
}

export interface CommunityTag {
  id: string;
  name: string;
  slug: string;
}

export interface CommunityPostImage {
  id: string;
  url: string;
}

export type CommunityPostSort =
  | "recent"
  | "popular"
  | "discussed"
  | "following"
  | "topics_following"
  | "unanswered";

export interface CommunityPostFilters {
  page?: number;
  pageSize?: number;
  category?: string;
  relatedWorkId?: string;
  q?: string;
  sort?: CommunityPostSort;
}

export interface CommunityPostSummary {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  category: CommunityPostCategory;
  author: CommunityAuthor;
  publishedAt: string;
  likeCount: number;
  commentCount: number;
  viewCount: number;
  viewerHasLiked: boolean;
  viewerHasBookmarked: boolean;
  tags: CommunityTag[];
  relatedWork: CommunityRelatedWork | null;
  images: CommunityPostImage[];
}

export interface CommunityPostDetail extends CommunityPostSummary {
  content: string;
}

export type CommunityPostStatus =
  | "DRAFT"
  | "PENDING"
  | "PUBLISHED"
  | "REJECTED"
  | "HIDDEN"
  | "DELETED";

export interface CommunityPostInput {
  title: string;
  content: string;
  categoryId: string;
  relatedWorkId?: string | null;
  imageMediaIds?: string[];
}

export interface CommunityPostWriteResult {
  id: string;
  slug: string;
  title: string;
  content: string;
  status: CommunityPostStatus;
  category: CommunityPostCategory;
  tags: CommunityTag[];
  relatedWork: CommunityRelatedWork | null;
  images: CommunityPostImage[];
  createdAt: string;
  updatedAt: string;
}

export type CommunityOwnerPostStatus =
  | "DRAFT"
  | "PENDING"
  | "PUBLISHED"
  | "REJECTED"
  | "HIDDEN";

export interface CommunityOwnerPost
  extends Omit<CommunityPostWriteResult, "status"> {
  status: CommunityOwnerPostStatus;
  moderationReason: string | null;
}

export interface CommunityAdminPost extends CommunityPostSummary {
  content: string;
  status: CommunityPostStatus;
  isPinned: boolean;
  commentsLocked: boolean;
  deletedAt: string | null;
  preDeleteStatus: CommunityPostStatus | null;
}

export type CommunityCommentVisibility = "VISIBLE" | "HIDDEN" | "DELETED";

export interface CommunityAdminPostPreview {
  id: string;
  slug: string;
  title: string;
}

export interface CommunityAdminComment extends CommunityCommentFields {
  visibility: CommunityCommentVisibility;
  post: CommunityAdminPostPreview;
}

export interface CommunityAdminMemberIdentity {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string | null;
  email?: string | null;
  hasPublicProfile?: boolean;
}

export type CommunityRestrictionScope = "POSTS" | "COMMENTS";
export type CommunityRestrictionStatus = "ACTIVE" | "EXPIRED" | "REVOKED";

export interface CommunityActiveRestrictionSummary {
  id: string;
  scope: CommunityRestrictionScope;
  expiresAt: string;
}

export interface CommunityAdminMember {
  member: CommunityAdminMemberIdentity;
  publishedPostCount: number;
  commentCount: number;
  followerCount: number;
  followingCount: number;
  lastActivityAt: string | null;
  activeRestrictions: CommunityActiveRestrictionSummary[];
}

export interface CommunityMemberRestriction {
  id: string;
  member: CommunityAdminMemberIdentity;
  scope: CommunityRestrictionScope;
  status: CommunityRestrictionStatus;
  reason: string;
  startsAt: string;
  expiresAt: string;
  actor: CommunityAuthor;
  requestId: string;
}

export interface CommunityMemberRestrictionCreateInput {
  scope: CommunityRestrictionScope;
  durationMinutes: number;
  reason: string;
}

export interface CommunityAdminPinResult {
  postId: string;
  isPinned: boolean;
}

export interface CommunityAdminCommentsLockResult {
  postId: string;
  commentsLocked: boolean;
}

export interface CommunityAdminPostDeletionResult {
  postId: string;
  isDeleted: boolean;
  deletedAt: string | null;
  restoredStatus: CommunityPostStatus | null;
}

export interface CommunityAdminCommentResult {
  commentId: string;
  visibility: CommunityCommentVisibility;
}

export type CommunityTargetType = "POST" | "COMMENT";

export type CommunityReportReason =
  | "SPAM"
  | "HARASSMENT"
  | "HATE_SPEECH"
  | "MISINFORMATION"
  | "COPYRIGHT"
  | "ADVERTISING"
  | "PRIVACY_VIOLATION"
  | "OTHER";

export type CommunityReportStatus = "OPEN" | "RESOLVED" | "DISMISSED";
export type CommunityReportResolutionAction = "HIDE" | "DISMISS";

export interface CommunityReportAuthor {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string | null;
}

export interface CommunityPostReportPreview {
  type: "POST";
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  author: CommunityReportAuthor;
}

export interface CommunityCommentReportPreview {
  type: "COMMENT";
  id: string;
  postId: string;
  postSlug: string;
  postTitle: string;
  content: string;
  isDeleted: boolean;
  author: CommunityReportAuthor | null;
}

export interface CommunityReport {
  id: string;
  targetType: CommunityTargetType;
  targetId: string;
  status: CommunityReportStatus;
  reason: CommunityReportReason;
  details: string | null;
  createdAt: string;
  resolvedAt: string | null;
  resolutionAction: CommunityReportResolutionAction | null;
  resolutionReason: string | null;
  reporter: CommunityReportAuthor;
  targetPreview: CommunityPostReportPreview | CommunityCommentReportPreview;
}

export interface CommunityReportSubmissionInput {
  reason: CommunityReportReason;
  details?: string;
}

export interface CommunityReportResolutionInput {
  action: CommunityReportResolutionAction;
  reason: string;
}

export type CommunityReportSubmissionResult = CommunityReport;

export interface CommunityVisibilityResult {
  targetType: CommunityTargetType;
  targetId: string;
  state: "HIDDEN" | "VISIBLE";
}

export interface CommunityAdminCategory extends CommunityCategory {
  isActive: boolean;
}

export interface CommunityAdminCategoryCreateInput {
  name: string;
  slug: string;
  description: string;
  icon?: string | null;
  sortOrder?: number;
  isActive?: boolean;
  reason: string;
}

export interface CommunityAdminCategoryUpdateInput {
  name?: string;
  slug?: string;
  description?: string;
  icon?: string | null;
  sortOrder?: number;
  isActive?: boolean;
  reason: string;
}

export type CommunityModerationTargetType =
  | CommunityTargetType
  | "CATEGORY"
  | "SETTINGS";

export interface CommunityModerationEvent {
  id: string;
  targetType: CommunityModerationTargetType;
  targetId: string;
  action: string;
  actorId: string;
  actor: CommunityReportAuthor;
  reason: string;
  requestId: string;
  createdAt: string;
}

export interface CommunityFeedMeta {
  requestId: string;
  page: number;
  pageSize: number;
  total: number;
}

export type CommunityPageResponse<Data> = Omit<
  SuccessEnvelope<Data>,
  "meta"
> & {
  meta: CommunityFeedMeta;
};

export type CommunityChatRoom = "MEMBER" | "COMPANION" | "PRESTIGE";

export interface CommunityChatRoomAccess {
  room: CommunityChatRoom;
  allowed: boolean;
  source: "TIER" | "MANUAL" | "ADMIN" | "NONE";
}

export interface CommunityChatRoomUserCandidate {
  userId: string;
  email: string;
  displayName: string;
}

export interface CommunityChatRoomGrant extends CommunityChatRoomUserCandidate {
  room: CommunityChatRoom;
  reason: string;
  grantedAt: string;
  grantedByUserId: string;
}

export type CommunityEventEntitlement = "TALK" | "CONNECT" | "CIRCLE";
export type CommunityEventStatus = "DRAFT" | "PUBLISHED" | "CANCELLED";
export type CommunityEventRegistrationStatus =
  | "CONFIRMED"
  | "WAITLISTED"
  | "CANCELLED"
  | "CANCELLED_LATE"
  | "CANCELLED_BY_EVENT"
  | "INELIGIBLE"
  | "PAYMENT_REQUIRED";

export interface CommunityEvent {
  id: string;
  title: string;
  description: string;
  startsAt: string;
  endsAt: string;
  registrationOpensAt: string | null;
  priorityTier: "COMPANION" | "PRESTIGE" | null;
  priorityOpensAt: string | null;
  location: string;
  requiredTier: MembershipTier;
  capacity: number;
  confirmedCount: number;
  ticketPriceMinor: number;
  cancellationCutoffAt: string | null;
  includedEntitlement: CommunityEventEntitlement | null;
  entitlementQuota: number | null;
  requiresDiamondApproval: boolean;
  status: CommunityEventStatus;
  createdByUserId: string;
  createdAt: string;
  updatedAt: string;
}

export interface CommunityEventRegistration {
  id: string;
  eventId: string;
  userId: string;
  status: CommunityEventRegistrationStatus;
  entitlementUnits: number;
  entitlementSnapshot: CommunityEventEntitlement | null;
  entitlementCycleStartedAt: string | null;
  membershipTierSnapshot: Exclude<MembershipTier, "MEMBER"> | null;
  registeredAt: string;
  cancelledAt: string | null;
}

export interface MyCommunityEventRegistration {
  registration: CommunityEventRegistration;
  event: CommunityEvent;
}

export interface CommunityEventInput {
  title: string;
  description: string;
  startsAt: string;
  endsAt: string;
  registrationOpensAt?: string | null;
  priorityTier?: "COMPANION" | "PRESTIGE" | null;
  priorityOpensAt?: string | null;
  location: string;
  requiredTier: MembershipTier;
  capacity: number;
  ticketPriceMinor: number;
  cancellationCutoffAt?: string | null;
  includedEntitlement?: CommunityEventEntitlement | null;
  entitlementQuota?: number | null;
  requiresDiamondApproval?: boolean;
}
export interface CommunityChatMessage {
  id: string;
  displayName: string;
  avatarUrl: string | null;
  body: string;
  tier: MembershipTier;
  createdAt: string;
  editedAt: string | null;
  isAdmin: boolean;
  canEdit: boolean;
  canRemove: boolean;
}

export interface CommunityChatPage {
  items: CommunityChatMessage[];
  hasMore: boolean;
  nextCursor: string | null;
}
