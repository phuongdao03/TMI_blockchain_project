import type {
  AccountType,
  ActivityPage,
  AuditLogItem,
  AuthUser,
  CmsBanner,
  CmsCategory,
  CmsPage,
  CmsPost,
  CmsPostInput,
  CouncilConflict,
  CouncilListFilters,
  CouncilMember,
  CouncilMinutes,
  CouncilSession,
  CouncilSessionDetail,
  CouncilSessionListItem,
  CouncilVote,
  CouncilVoteChoice,
  Certificate,
  CertificateDetail,
  CertificateDownload,
  ContentReportAccepted,
  ContentReportAdmin,
  ContentReportReason,
  ContentReportStatus,
  Dossier,
  DossierDetail,
  DossierEvidence,
  DossierInput,
  DossierListFilters,
  DossierPatch,
  DossierSubmission,
  DossierTimelineItem,
  DossierVersion,
  EvidenceInput,
  ErrorEnvelope,
  ListResponseMeta,
  LoginData,
  MediaAsset,
  MediaUploadAuthorization,
  MediaUploadCompletion,
  MediaUploadIntent,
  MemberInput,
  MessageData,
  Organization,
  OrganizationInput,
  OrganizationMember,
  NotificationItem,
  OAuthStartData,
  OperationsMetrics,
  PaymentOrder,
  ProfileUpdate,
  PublicAsset,
  PublicAssetDetail,
  PublicCategory,
  PublicCatalogFilters,
  PublicCatalogWork,
  PublicMapMarker,
  PublicationStatus,
  PublicWorkAdmin,
  PublicWorkCategory,
  PublicWorkEditor,
  PublicWorkDetail,
  PublicWorkEditorInput,
  PublicWorkMedia,
  PublicWorkPreview,
  SearchAutocompleteSuggestion,
  SearchFacets,
  SearchHistoryRecorded,
  SearchHistoryState,
  SearchAnalytics,
  SearchRelatedWork,
  SearchTrendingItem,
  SearchParameters,
  SearchResponse,
  PublicWorkTag,
  ProfileAvatarUpdate,
  StatusData,
  SignedDelivery,
  SuccessEnvelope,
  UserProfile,
  ReviewAssignment,
  ReviewAssignmentDetail,
  ReviewAssignmentSummary,
  ReviewData,
  ReviewDraft,
  ReviewListFilters,
  Verification,
  VotingCampaign,
  VoteHistoryItem,
  PublicVotingCampaign,
  PublicCampaignWork,
  PublicVoteSummary,
  PublicRankingData,
  VotingEligibility,
  VoteMutationResult,
  CampaignParticipant,
  CampaignParticipantStatus,
} from "@/lib/api/types";

const API_ROOT = "/api/v1";
const CSRF_COOKIE_NAME = "tmi_csrf";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") {
    return undefined;
  }
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : undefined;
}

function isMutation(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method);
}

async function parseResponse<Data>(
  response: Response,
): Promise<SuccessEnvelope<Data>> {
  if (response.status === 204) {
    return {
      success: true,
      data: undefined as Data,
      meta: { request_id: response.headers.get("X-Request-Id") ?? "" },
    };
  }
  const payload = (await response.json()) as
    | SuccessEnvelope<Data>
    | ErrorEnvelope;
  if (!response.ok || !payload.success) {
    const error = payload.success ? undefined : payload.error;
    throw new ApiError(
      error?.message ?? "Yêu cầu không thành công. Vui lòng thử lại.",
      error?.code ?? "REQUEST_FAILED",
      response.status,
    );
  }
  return payload;
}

async function requestEnvelope<Data>(
  path: string,
  init: RequestInit = {},
  allowRefresh = true,
): Promise<SuccessEnvelope<Data>> {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (isMutation(method)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME);
    if (csrfToken) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  const refreshable =
    response.status === 401 &&
    allowRefresh &&
    Boolean(readCookie(CSRF_COOKIE_NAME)) &&
    !["/auth/login", "/auth/refresh"].includes(path);
  if (refreshable) {
    try {
      await requestEnvelope<StatusData>(
        "/auth/refresh",
        { method: "POST" },
        false,
      );
      return requestEnvelope<Data>(path, init, false);
    } catch {
      // Preserve the original endpoint's authentication failure.
    }
  }
  return parseResponse<Data>(response);
}

async function request<Data>(
  path: string,
  init: RequestInit = {},
): Promise<Data> {
  return (await requestEnvelope<Data>(path, init)).data;
}

async function requestPaginated<Data>(
  path: string,
): Promise<Omit<SuccessEnvelope<Data>, "meta"> & { meta: ListResponseMeta }> {
  return requestEnvelope<Data>(path) as Promise<
    Omit<SuccessEnvelope<Data>, "meta"> & { meta: ListResponseMeta }
  >;
}

export const authApi = {
  register(email: string, password: string, accountType: AccountType) {
    return request<MessageData>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, accountType }),
    });
  },
  login(email: string, password: string, deviceName: string) {
    return request<LoginData>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, deviceName }),
    });
  },
  startGoogle(accountType: AccountType, next?: string) {
    return request<OAuthStartData>("/auth/oauth/google/start", {
      method: "POST",
      body: JSON.stringify({ accountType, ...(next ? { next } : {}) }),
    });
  },
  upgradeToApplicant(accountType: Exclude<AccountType, "PUBLIC_USER">) {
    return request<AuthUser>("/auth/applicant-upgrade", {
      method: "POST",
      body: JSON.stringify({ accountType }),
    });
  },
  verifyEmail(token: string) {
    return request<StatusData>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },
  forgotPassword(email: string) {
    return request<MessageData>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  resetPassword(token: string, newPassword: string) {
    return request<StatusData>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, newPassword }),
    });
  },
  async currentUser(): Promise<AuthUser | null> {
    try {
      return await request<AuthUser>("/auth/me");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        return null;
      }
      throw error;
    }
  },
};

export const cmsApi = {
  list(page = 1) {
    return requestPaginated<CmsPost[]>(
      `/admin/cms/posts?page=${page}&pageSize=20`,
    );
  },
  create(input: CmsPostInput) {
    return request<CmsPost>("/admin/cms/posts", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  publish(id: string) {
    return request<CmsPost>(`/admin/cms/posts/${id}/publish`, {
      method: "POST",
    });
  },
  listPages() {
    return request<CmsPage[]>("/admin/cms/pages");
  },
  createPage(input: { title: string; slug: string; bodyHtml: string }) {
    return request<CmsPage>("/admin/cms/pages", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  publishPage(id: string) {
    return request<CmsPage>(`/admin/cms/pages/${id}/publish`, {
      method: "POST",
    });
  },
  listBanners() {
    return request<CmsBanner[]>("/admin/cms/banners");
  },
  createBanner(input: {
    title: string;
    slug: string;
    imageUrl: string;
    linkUrl: string | null;
  }) {
    return request<CmsBanner>("/admin/cms/banners", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  publishBanner(id: string) {
    return request<CmsBanner>(`/admin/cms/banners/${id}/publish`, {
      method: "POST",
    });
  },
  listCategories() {
    return request<CmsCategory[]>("/admin/cms/categories");
  },
  createCategory(input: {
    name: string;
    slug: string;
    description: string | null;
  }) {
    return request<CmsCategory>("/admin/cms/categories", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
};

export const operationsApi = {
  metrics() {
    return request<OperationsMetrics>("/admin/operations/metrics");
  },
};

export const notificationApi = {
  list(page = 1) {
    return requestPaginated<NotificationItem[]>(
      `/notifications?page=${page}&pageSize=20`,
    );
  },
  unreadCount() {
    return request<{ unreadCount: number }>("/notifications/unread-count");
  },
  markRead(id: string) {
    return request<NotificationItem>(`/notifications/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ read: true }),
    });
  },
};

export const votingApi = {
  campaigns(page = 1) {
    return requestPaginated<PublicVotingCampaign[]>(
      `/public/campaigns?page=${page}&pageSize=20`,
    );
  },
  campaign(slug: string) {
    return request<PublicVotingCampaign>(`/public/campaigns/${slug}`);
  },
  works(slug: string) {
    return request<PublicCampaignWork[]>(`/public/campaigns/${slug}/works`);
  },
  summary(slug: string) {
    return request<PublicVoteSummary[]>(
      `/public/campaigns/${slug}/vote-summary`,
    );
  },
  eligibility(campaignId: string, workId?: string) {
    const query = workId ? `?workId=${encodeURIComponent(workId)}` : "";
    return request<VotingEligibility>(
      `/campaigns/${campaignId}/eligibility${query}`,
    );
  },
  createVote(campaignId: string, workId: string, idempotencyKey: string) {
    return request<VoteMutationResult>(
      `/campaigns/${campaignId}/works/${workId}/votes`,
      { method: "POST", headers: { "Idempotency-Key": idempotencyKey } },
    );
  },
  changeVote(
    campaignId: string,
    sourceVoteId: string,
    targetWorkId: string,
    idempotencyKey: string,
  ) {
    return request<VoteMutationResult>(
      `/campaigns/${campaignId}/votes/change`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({ sourceVoteId, targetWorkId }),
      },
    );
  },
  revokeVote(campaignId: string, workId: string, idempotencyKey: string) {
    return request<VoteMutationResult>(
      `/campaigns/${campaignId}/works/${workId}/votes`,
      { method: "DELETE", headers: { "Idempotency-Key": idempotencyKey } },
    );
  },
  myVotes(page = 1, campaignId?: string) {
    const filter = campaignId
      ? `&campaignId=${encodeURIComponent(campaignId)}`
      : "";
    return requestPaginated<VoteHistoryItem[]>(
      `/me/votes?page=${page}&pageSize=20${filter}`,
    );
  },
};

export const rankingApi = {
  public(
    campaignSlug: string,
    options: {
      page?: number;
      pageSize?: number;
      version?: number;
      categoryId?: string;
    } = {},
  ) {
    const parameters = new URLSearchParams({
      page: String(options.page ?? 1),
      pageSize: String(options.pageSize ?? 20),
    });
    if (options.version !== undefined)
      parameters.set("version", String(options.version));
    if (options.categoryId) parameters.set("categoryId", options.categoryId);
    return request<PublicRankingData>(
      `/public/campaigns/${encodeURIComponent(campaignSlug)}/ranking?${parameters.toString()}`,
    );
  },
};

export const auditApi = {
  list(page = 1) {
    return requestPaginated<AuditLogItem[]>(
      `/admin/audit?page=${page}&pageSize=20`,
    );
  },
};

export const profileApi = {
  get() {
    return request<UserProfile>("/users/me");
  },
  update(profile: ProfileUpdate) {
    return request<UserProfile>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(profile),
    });
  },
  updateAvatar(profile: ProfileAvatarUpdate) {
    return request<UserProfile>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(profile),
    });
  },
};

export const mediaApi = {
  createUploadSignature(intent: MediaUploadIntent) {
    return request<MediaUploadAuthorization>("/media/upload-signature", {
      method: "POST",
      body: JSON.stringify(intent),
    });
  },
  completeUpload(completion: MediaUploadCompletion) {
    return request<MediaAsset>("/media/complete", {
      method: "POST",
      body: JSON.stringify(completion),
    });
  },
  signedUrl(mediaId: string) {
    return request<SignedDelivery>(`/media/${mediaId}/signed-url`);
  },
};

export const organizationApi = {
  list(page = 1, pageSize = 20) {
    return requestPaginated<Organization[]>(
      `/organizations?page=${page}&pageSize=${pageSize}`,
    );
  },
  create(organization: OrganizationInput) {
    return request<Organization>("/organizations", {
      method: "POST",
      body: JSON.stringify(organization),
    });
  },
  update(organizationId: string, organization: OrganizationInput) {
    return request<Organization>(`/organizations/${organizationId}`, {
      method: "PATCH",
      body: JSON.stringify({
        legalName: organization.legalName,
        displayName: organization.displayName,
        taxCode: organization.taxCode,
      }),
    });
  },
  archive(organizationId: string) {
    return request<StatusData>(`/organizations/${organizationId}`, {
      method: "DELETE",
    });
  },
  listMembers(organizationId: string, page = 1, pageSize = 20) {
    return requestPaginated<OrganizationMember[]>(
      `/organizations/${organizationId}/members?page=${page}&pageSize=${pageSize}`,
    );
  },
  addMember(organizationId: string, member: MemberInput) {
    return request<OrganizationMember>(
      `/organizations/${organizationId}/members`,
      {
        method: "POST",
        body: JSON.stringify(member),
      },
    );
  },
  removeMember(organizationId: string, userId: string) {
    return request<StatusData>(
      `/organizations/${organizationId}/members/${userId}`,
      { method: "DELETE" },
    );
  },
};

export const dossierApi = {
  list(filters: DossierListFilters = {}) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: String(filters.pageSize ?? 20),
    });
    if (filters.status) parameters.set("status", filters.status);
    if (filters.categoryId) {
      parameters.set("categoryId", filters.categoryId);
    }
    return requestPaginated<Dossier[]>(`/dossiers?${parameters.toString()}`);
  },
  get(dossierId: string) {
    return request<DossierDetail>(`/dossiers/${dossierId}`);
  },
  create(dossier: DossierInput) {
    return request<Dossier>("/dossiers", {
      method: "POST",
      body: JSON.stringify(dossier),
    });
  },
  update(dossierId: string, dossier: DossierPatch) {
    return request<Dossier>(`/dossiers/${dossierId}`, {
      method: "PATCH",
      body: JSON.stringify(dossier),
    });
  },
  remove(dossierId: string) {
    return request<StatusData>(`/dossiers/${dossierId}`, {
      method: "DELETE",
    });
  },
  attachEvidence(dossierId: string, evidence: EvidenceInput) {
    return request<DossierEvidence>(`/dossiers/${dossierId}/evidences`, {
      method: "POST",
      body: JSON.stringify(evidence),
    });
  },
  removeEvidence(dossierId: string, evidenceId: string) {
    return request<StatusData>(
      `/dossiers/${dossierId}/evidences/${evidenceId}`,
      { method: "DELETE" },
    );
  },
  submit(dossierId: string, idempotencyKey: string) {
    return request<DossierSubmission>(`/dossiers/${dossierId}/submit`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },
  resubmit(dossierId: string, idempotencyKey: string) {
    return request<DossierSubmission>(`/dossiers/${dossierId}/resubmit`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },
  versions(dossierId: string) {
    return request<DossierVersion[]>(`/dossiers/${dossierId}/versions`);
  },
  timeline(dossierId: string) {
    return request<DossierTimelineItem[]>(`/dossiers/${dossierId}/timeline`);
  },
};

export const paymentApi = {
  create(dossierId: string, idempotencyKey: string) {
    return request<PaymentOrder>(`/dossiers/${dossierId}/payment-orders`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },
  get(orderId: string) {
    return request<PaymentOrder>(`/payment-orders/${orderId}`);
  },
};

export const reviewApi = {
  list(filters: ReviewListFilters = {}) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: String(filters.pageSize ?? 20),
    });
    if (filters.status) parameters.set("status", filters.status);
    return requestPaginated<ReviewAssignmentSummary[]>(
      `/reviewer/assignments?${parameters.toString()}`,
    );
  },
  get(assignmentId: string) {
    return request<ReviewAssignmentDetail>(
      `/reviewer/assignments/${assignmentId}`,
    );
  },
  declareConflict(
    assignmentId: string,
    input: { hasConflict: boolean; reason: string | null },
  ) {
    return request<ReviewAssignment>(
      `/reviewer/assignments/${assignmentId}/conflict`,
      {
        method: "POST",
        body: JSON.stringify(input),
      },
    );
  },
  saveDraft(assignmentId: string, draft: ReviewDraft) {
    return request<ReviewData>(`/reviewer/assignments/${assignmentId}/draft`, {
      method: "PUT",
      body: JSON.stringify(draft),
    });
  },
  submit(assignmentId: string) {
    return request<ReviewData>(`/reviewer/assignments/${assignmentId}/submit`, {
      method: "POST",
    });
  },
};

export const councilApi = {
  list(filters: CouncilListFilters = {}) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: String(filters.pageSize ?? 20),
    });
    if (filters.status) parameters.set("status", filters.status);
    return requestPaginated<CouncilSessionListItem[]>(
      `/council/sessions?${parameters.toString()}`,
    );
  },
  get(sessionId: string) {
    return request<CouncilSessionDetail>(`/council/sessions/${sessionId}`);
  },
  confirmAttendance(sessionId: string) {
    return request<CouncilMember>(`/council/sessions/${sessionId}/attendance`, {
      method: "POST",
    });
  },
  open(sessionId: string) {
    return request<CouncilSession>(
      `/admin/council/sessions/${sessionId}/open`,
      { method: "POST" },
    );
  },
  close(sessionId: string) {
    return request<CouncilSession>(
      `/admin/council/sessions/${sessionId}/close`,
      { method: "POST" },
    );
  },
  declareConflict(
    caseId: string,
    input: { hasConflict: boolean; reason: string | null },
  ) {
    return request<CouncilConflict>(`/council/cases/${caseId}/conflict`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  vote(caseId: string, input: { choice: CouncilVoteChoice; reason: string }) {
    return request<CouncilVote>(`/council/cases/${caseId}/vote`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  minutes(sessionId: string) {
    return request<CouncilMinutes>(`/council/sessions/${sessionId}/minutes`);
  },
};

export const certificateApi = {
  list(page = 1, pageSize = 20) {
    return requestPaginated<Certificate[]>(
      `/certificates?page=${page}&pageSize=${pageSize}`,
    );
  },
  get(certificateId: string) {
    return request<CertificateDetail>(`/certificates/${certificateId}`);
  },
  download(certificateId: string) {
    return request<CertificateDownload>(
      `/certificates/${certificateId}/download`,
    );
  },
};

export const publicApi = {
  autocomplete(query: string, signal?: AbortSignal) {
    const parameters = new URLSearchParams({ q: query });
    return request<SearchAutocompleteSuggestion[]>(
      `/public/search/autocomplete?${parameters.toString()}`,
      { signal },
    );
  },
  search(filters: SearchParameters, signal?: AbortSignal) {
    return requestEnvelope<SearchResponse["data"]>(
      `/public/search?${publicSearchParameters(filters, true).toString()}`,
      { signal },
    ) as unknown as Promise<SearchResponse>;
  },
  searchFacets(filters: SearchParameters, signal?: AbortSignal) {
    return request<SearchFacets>(
      `/public/search/facets?${publicSearchParameters(filters, false).toString()}`,
      { signal },
    );
  },
  trending(period: "HOURLY" | "DAILY" = "DAILY", limit = 10) {
    return request<SearchTrendingItem[]>(
      `/public/discovery/trending?period=${period}&limit=${limit}`,
    );
  },
  related(slug: string, limit = 6) {
    return request<SearchRelatedWork[]>(
      `/public/works/${encodeURIComponent(slug)}/related?limit=${limit}`,
    );
  },
  recordSearchClick(requestId: string, workId: string) {
    return request<{ recorded: boolean }>("/public/search/clicks", {
      method: "POST",
      body: JSON.stringify({ requestId, workId }),
    });
  },
  categories() {
    return request<PublicCategory[]>("/public/categories");
  },
  assets(filters: { query?: string; category?: string; page?: number } = {}) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: "12",
    });
    if (filters.query) parameters.set("query", filters.query);
    if (filters.category) parameters.set("category", filters.category);
    return requestPaginated<PublicAsset[]>(
      `/public/assets?${parameters.toString()}`,
    );
  },
  asset(slug: string) {
    return request<PublicAssetDetail>(
      `/public/assets/${encodeURIComponent(slug)}`,
    );
  },
  map(category?: string) {
    const suffix = category ? `?category=${encodeURIComponent(category)}` : "";
    return request<PublicMapMarker[]>(`/public/map${suffix}`);
  },
  works(filters: PublicCatalogFilters = {}) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: String(filters.pageSize ?? 12),
      sort: filters.sort ?? "newest",
    });
    if (filters.query) parameters.set("query", filters.query);
    if (filters.category) parameters.set("category", filters.category);
    if (filters.tag) parameters.set("tag", filters.tag);
    if (filters.publishedFrom) {
      parameters.set(
        "publishedFrom",
        /^\d{4}-\d{2}-\d{2}$/.test(filters.publishedFrom)
          ? `${filters.publishedFrom}T00:00:00Z`
          : filters.publishedFrom,
      );
    }
    if (filters.publishedTo) {
      parameters.set(
        "publishedTo",
        /^\d{4}-\d{2}-\d{2}$/.test(filters.publishedTo)
          ? `${filters.publishedTo}T23:59:59Z`
          : filters.publishedTo,
      );
    }
    return requestPaginated<PublicCatalogWork[]>(
      `/public/works?${parameters.toString()}`,
    );
  },
  featuredWorks(limit = 6) {
    return request<PublicCatalogWork[]>(
      `/public/works/featured?limit=${limit}`,
    );
  },
  work(slug: string) {
    return request<PublicWorkDetail>(
      `/public/works/${encodeURIComponent(slug)}`,
    );
  },
  recordView(slug: string) {
    return request<void>(
      `/public/works/${encodeURIComponent(slug)}/engagement/views`,
      { method: "POST" },
    );
  },
  recordShare(slug: string, channel: "NATIVE" | "COPY_LINK") {
    return request<{ accepted: boolean }>(
      `/public/works/${encodeURIComponent(slug)}/engagement/shares`,
      {
        method: "POST",
        body: JSON.stringify({ channel }),
      },
    );
  },
  reportWork(
    workId: string,
    input: {
      reason: ContentReportReason;
      description: string | null;
      reporterEmail: string | null;
      captchaToken?: string | null;
    },
  ) {
    return request<ContentReportAccepted>(`/public/works/${workId}/reports`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },
  tags() {
    return request<PublicWorkTag[]>("/public/tags");
  },
  verifyToken(token: string) {
    return request<Verification>(`/verify/${encodeURIComponent(token)}`);
  },
  verifyNumber(number: string) {
    return request<Verification>(
      `/verify/certificate/${encodeURIComponent(number)}`,
    );
  },
  verifyTransaction(transactionHash: string) {
    return request<Verification>(
      `/verify/transaction/${encodeURIComponent(transactionHash)}`,
    );
  },
};

export const searchAnalyticsApi = {
  get(filters: { start: string; end: string; category?: string }) {
    const parameters = new URLSearchParams({
      start: filters.start,
      end: filters.end,
    });
    if (filters.category) parameters.set("category", filters.category);
    return request<SearchAnalytics>(
      `/admin/search/analytics?${parameters.toString()}`,
    );
  },
  exportUrl(filters: { start: string; end: string; category?: string }) {
    const parameters = new URLSearchParams({
      start: filters.start,
      end: filters.end,
    });
    if (filters.category) parameters.set("category", filters.category);
    return `${API_ROOT}/admin/search/analytics/export?${parameters.toString()}`;
  },
};

export const activityApi = {
  list(cursor?: string, pageSize = 20) {
    const parameters = new URLSearchParams({ pageSize: String(pageSize) });
    if (cursor) parameters.set("cursor", cursor);
    return request<ActivityPage>(`/me/activity?${parameters.toString()}`);
  },
};

export const searchHistoryApi = {
  get() {
    return request<SearchHistoryState>("/me/search-history");
  },
  setConsent(isEnabled: boolean) {
    return request<SearchHistoryState>("/me/search-history", {
      method: "PUT",
      body: JSON.stringify({ isEnabled }),
    });
  },
  record(query: string) {
    return request<SearchHistoryRecorded>("/me/search-history", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },
  clear() {
    return request<void>("/me/search-history", { method: "DELETE" });
  },
};

function publicSearchParameters(
  filters: SearchParameters,
  includeResultControls: boolean,
): URLSearchParams {
  const parameters = new URLSearchParams();
  if (filters.q) parameters.set("q", filters.q);
  if (filters.category) parameters.set("category", filters.category);
  if (filters.tags.length) parameters.set("tags", filters.tags.join(","));
  if (filters.tagsMode !== "any") parameters.set("tagsMode", filters.tagsMode);
  if (filters.organization)
    parameters.set("organization", filters.organization);
  if (filters.publishedFrom) {
    parameters.set("publishedFrom", `${filters.publishedFrom}T00:00:00Z`);
  }
  if (filters.publishedTo) {
    parameters.set("publishedTo", `${filters.publishedTo}T23:59:59Z`);
  }
  if (filters.hasBlockchainProof !== undefined) {
    parameters.set("hasBlockchainProof", String(filters.hasBlockchainProof));
  }
  if (filters.certificateStatus) {
    parameters.set("certificateStatus", filters.certificateStatus);
  }
  if (includeResultControls) {
    parameters.set("sort", filters.sort);
    parameters.set("pageSize", "20");
    if (filters.cursor) parameters.set("cursor", filters.cursor);
  }
  return parameters;
}

export const contentReportAdminApi = {
  list(status?: ContentReportStatus, page = 1) {
    const parameters = new URLSearchParams({
      page: String(page),
      pageSize: "20",
    });
    if (status) parameters.set("status", status);
    return requestPaginated<ContentReportAdmin[]>(
      `/admin/content-reports?${parameters.toString()}`,
    );
  },
  transition(
    reportId: string,
    status: ContentReportStatus,
    resolutionNote: string | null,
  ) {
    return request<ContentReportAdmin>(`/admin/content-reports/${reportId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, resolutionNote }),
    });
  },
  suspend(report: ContentReportAdmin, reason: string) {
    return request<ContentReportAdmin>(
      `/admin/content-reports/${report.id}/suspend`,
      {
        method: "POST",
        body: JSON.stringify({
          expectedWorkVersion: report.workVersion,
          reason,
        }),
      },
    );
  },
};

export const publicWorkAdminApi = {
  list(
    filters: {
      query?: string;
      status?: PublicationStatus;
      page?: number;
      pageSize?: number;
    } = {},
  ) {
    const parameters = new URLSearchParams({
      page: String(filters.page ?? 1),
      pageSize: String(filters.pageSize ?? 20),
    });
    if (filters.query) parameters.set("query", filters.query);
    if (filters.status) parameters.set("status", filters.status);
    return requestPaginated<PublicWorkAdmin[]>(
      `/admin/public-works?${parameters.toString()}`,
    );
  },
  get(workId: string) {
    return request<PublicWorkEditor>(`/admin/public-works/${workId}`);
  },
  update(workId: string, input: PublicWorkEditorInput) {
    return request<PublicWorkEditor>(`/admin/public-works/${workId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },
  preview(workId: string) {
    return request<PublicWorkPreview>(`/admin/public-works/${workId}/preview`);
  },
  categories() {
    return request<PublicWorkCategory[]>("/admin/public-works/categories");
  },
  tags() {
    return request<PublicWorkTag[]>("/admin/public-works/tags");
  },
  assignTags(workId: string, tagIds: string[]) {
    return request<void>(`/admin/public-works/${workId}/tags`, {
      method: "PUT",
      body: JSON.stringify({ tagIds }),
    });
  },
  media(workId: string) {
    return request<PublicWorkMedia[]>(`/admin/public-works/${workId}/media`);
  },
  attachMedia(workId: string, mediaAssetId: string, sortOrder: number) {
    return request<PublicWorkMedia>(`/admin/public-works/${workId}/media`, {
      method: "POST",
      body: JSON.stringify({ mediaAssetId, sortOrder }),
    });
  },
  reorderMedia(workId: string, relationIds: string[]) {
    return request<void>(`/admin/public-works/${workId}/media/order`, {
      method: "PUT",
      body: JSON.stringify({ relationIds }),
    });
  },
  removeMedia(workId: string, relationId: string) {
    return request<void>(`/admin/public-works/${workId}/media/${relationId}`, {
      method: "DELETE",
    });
  },
  publish(workId: string, expectedVersion: number) {
    return request<PublicWorkAdmin>(`/admin/public-works/${workId}/publish`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, visibility: "PUBLIC" }),
    });
  },
  transition(
    workId: string,
    action: "hide" | "suspend" | "archive",
    expectedVersion: number,
    reason?: string,
  ) {
    return request<PublicWorkAdmin>(`/admin/public-works/${workId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, ...(reason ? { reason } : {}) }),
    });
  },
};

export const votingCampaignAdminApi = {
  list() {
    return requestPaginated<VotingCampaign[]>(
      "/admin/voting/campaigns?page=1&pageSize=100",
    );
  },
  participants(campaignId: string, status?: CampaignParticipantStatus) {
    const parameters = new URLSearchParams({ page: "1", pageSize: "100" });
    if (status) parameters.set("status", status);
    return requestPaginated<CampaignParticipant[]>(
      `/admin/voting/campaigns/${campaignId}/participants?${parameters.toString()}`,
    );
  },
  add(campaignId: string, workId: string, reason: string) {
    return request<CampaignParticipant>(
      `/admin/voting/campaigns/${campaignId}/participants`,
      { method: "POST", body: JSON.stringify({ workId, reason }) },
    );
  },
  bulkAdd(campaignId: string, workIds: string[], reason: string) {
    return request<CampaignParticipant[]>(
      `/admin/voting/campaigns/${campaignId}/participants/bulk`,
      { method: "POST", body: JSON.stringify({ workIds, reason }) },
    );
  },
  transition(
    campaignId: string,
    participantId: string,
    action: "approve" | "remove",
    reason: string,
  ) {
    return request<CampaignParticipant>(
      `/admin/voting/campaigns/${campaignId}/participants/${participantId}/${action}`,
      { method: "POST", body: JSON.stringify({ reason }) },
    );
  },
};
