import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  adminAffiliateApi,
  adminReviewApi,
  adminUsersApi,
  auditApi,
  authApi,
  affiliateApi,
  dossierApi,
  employeeInvitationsApi,
  feeApi,
  hrAdminAttendanceApi,
  hrAdminLeaveApi,
  hrAdminOvertimeApi,
  hrDepartmentApi,
  hrDashboardApi,
  hrEmployeeApi,
  hrModeratorDashboardApi,
  hrPayrollApi,
  mediaApi,
  membershipApi,
  organizationApi,
  profileApi,
  publicApi,
  staffAccountsApi,
  staffInvitationsApi,
  taskAdminApi,
} from "@/lib/api/client";

describe("admin review API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("lists the handoff queue and assigns a reviewer", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        response({
          success: true,
          data: [],
          meta: { requestId: "review-queue", page: 1, pageSize: 20, total: 0 },
        }),
      )
      .mockResolvedValueOnce(
        response({ success: true, data: [], meta: { requestId: "assign" } }),
      );

    await adminReviewApi.list({ status: "UNDER_REVIEW" });
    await adminReviewApi.assign("dossier/1", ["reviewer-1"], "2026-09-10");

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/review-dossiers?page=1&pageSize=20&status=UNDER_REVIEW",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/admin/dossiers/dossier%2F1/assign-reviewers",
    );
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({
        reviewerUserIds: ["reviewer-1"],
        dueAt: "2026-09-10",
      }),
    });
  });
});

describe("fee policy API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("sends the explicit activation confirmation", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: { id: "policy-1", status: "ACTIVE" },
        meta: { requestId: "policy-approve" },
      }),
    );

    await feeApi.approvePolicy("policy/1", true);

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/fee-policies/policy%2F1/approve",
    );
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ confirmActivation: true }),
    });
  });
});

describe("admin users API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("sends server-side list filters and an audited status change", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: [],
        meta: { request_id: "users-list", page: 2, pageSize: 25, total: 0 },
      }),
    );

    await adminUsersApi.list({
      page: 2,
      pageSize: 25,
      search: "an@example.com",
      status: "ACTIVE",
      provider: "GOOGLE",
      verified: true,
      sortBy: "email",
      sortOrder: "asc",
    });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/users?page=2&pageSize=25&search=an%40example.com&status=ACTIVE&provider=GOOGLE&verified=true&sortBy=email&sortOrder=asc",
    );

    fetchMock.mockResolvedValueOnce(
      response({
        success: true,
        data: { id: "user-1", status: "SUSPENDED" },
        meta: { request_id: "user-status" },
      }),
    );
    await adminUsersApi.changeStatus("user-1", {
      status: "SUSPENDED",
      expectedStatus: "ACTIVE",
      reason: "Yeu cau tu bo phan an toan",
    });
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/admin/users/user-1/status",
    );
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("PATCH");
    expect(
      new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("csrf-value");
  });
});

function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("membership chat API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("requests opaque cursor pages and exposes chat mutations", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        response({ success: true, data: {}, meta: { requestId: "chat" } }),
      );

    await membershipApi.messages("MEMBER", {
      cursor: "room+cursor/",
      limit: 100,
    });
    await membershipApi.send("MEMBER", "Hello");
    await membershipApi.editMessage("message-1", "Updated");
    await membershipApi.removeMessage("message-1");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/community/chat/MEMBER/messages?limit=100&cursor=room%2Bcursor%2F",
      "/api/v1/community/chat/MEMBER/messages",
      "/api/v1/community/chat/messages/message-1",
      "/api/v1/community/chat/messages/message-1",
    ]);
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ body: "Hello" }),
    });
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({
      method: "PATCH",
      body: JSON.stringify({ body: "Updated" }),
    });
    for (const index of [1, 2, 3]) {
      expect(
        new Headers(fetchMock.mock.calls[index]?.[1]?.headers).get(
          "X-CSRF-Token",
        ),
      ).toBe("csrf-value");
    }
  });
});

describe("auth API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("passes affiliate attribution into Firebase exchange", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: {},
        meta: { request_id: "affiliate-exchange" },
      }),
    );

    await authApi.exchangeFirebaseToken(
      "x".repeat(100),
      "PUBLIC_USER",
      "/workspace",
      {
        referralCode: "THV-ABC123",
        referralClickId: "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
      },
    );

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/auth/firebase/exchange");
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({
        idToken: "x".repeat(100),
        accountType: "PUBLIC_USER",
        next: "/workspace",
        referralCode: "THV-ABC123",
        referralClickId: "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
      }),
    );
  });

  it("records referral clicks with the stable client event id", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: {
          id: "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
          createdAt: "2026-11-05T00:00:00Z",
        },
        meta: { request_id: "referral-click" },
      }),
    );

    await affiliateApi.recordReferralClick(
      "THV-ABC123",
      "7b6257d9-c9d3-4461-8805-4b88cfaea282",
    );

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/affiliate/referral-clicks",
    );
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({
        referralCode: "THV-ABC123",
        eventId: "7b6257d9-c9d3-4461-8805-4b88cfaea282",
      }),
    );
  });

  it("rotates once on an expired access cookie and retries /me", async () => {
    const user = {
      id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
      email: "owner@cnsgroup.vn",
      roles: ["USER"],
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        response(
          {
            success: false,
            error: {
              code: "UNAUTHENTICATED",
              message: "Authentication is required.",
              details: {},
              request_id: "request-1",
            },
          },
          401,
        ),
      )
      .mockResolvedValueOnce(
        response({
          success: true,
          data: { status: "refreshed" },
          meta: { request_id: "request-2" },
        }),
      )
      .mockResolvedValueOnce(
        response({
          success: true,
          data: user,
          meta: { request_id: "request-3" },
        }),
      );

    await expect(authApi.currentUser()).resolves.toEqual(user);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const [, refreshInit] = fetchMock.mock.calls[1] ?? [];
    expect(new Headers(refreshInit?.headers).get("X-CSRF-Token")).toBe(
      "csrf-value",
    );
  });

  it("does not call refresh while bootstrapping a signed-out browser", async () => {
    document.cookie = "cns_csrf=; Max-Age=0; Path=/";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response(
        {
          success: false,
          error: {
            code: "UNAUTHENTICATED",
            message: "Authentication is required.",
            details: {},
            request_id: "request-4",
          },
        },
        401,
      ),
    );

    await expect(authApi.currentUser()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("keeps the backend request id on API errors for support tracing", async () => {
    document.cookie = "cns_csrf=; Max-Age=0; Path=/";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response(
        {
          success: false,
          error: {
            code: "INTERNAL_SERVER_ERROR",
            message: "An unexpected error occurred.",
            details: {},
            request_id: "decision-request-123",
          },
        },
        500,
      ),
    );

    await expect(authApi.currentUser()).rejects.toMatchObject({
      code: "INTERNAL_SERVER_ERROR",
      requestId: "decision-request-123",
      status: 500,
    });
  });

  it("shares one refresh across concurrent authenticated requests", async () => {
    let resourceCalls = 0;
    let refreshCalls = 0;
    let releaseInitialRequests: (() => void) | undefined;
    const initialRequestsReady = new Promise<void>((resolve) => {
      releaseInitialRequests = resolve;
    });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const url = String(input);
        if (url.endsWith("/api/v1/dossiers/types")) {
          resourceCalls += 1;
          if (resourceCalls <= 2) {
            if (resourceCalls === 2) releaseInitialRequests?.();
            await initialRequestsReady;
            return response(
              {
                success: false,
                error: {
                  code: "UNAUTHENTICATED",
                  message: "Authentication is required.",
                },
              },
              401,
            );
          }
          return response({
            success: true,
            data: [],
            meta: { request_id: `dossier-types-${resourceCalls}` },
          });
        }
        if (url.endsWith("/api/v1/auth/refresh")) {
          refreshCalls += 1;
          return refreshCalls === 1
            ? response({
                success: true,
                data: { status: "refreshed" },
                meta: { request_id: "refresh" },
              })
            : response(
                {
                  success: false,
                  error: {
                    code: "UNAUTHENTICATED",
                    message: "Authentication is required.",
                  },
                },
                401,
              );
        }
        throw new Error(`Unexpected request: ${url}`);
      });

    await expect(
      Promise.all([dossierApi.listTypes(), dossierApi.listTypes()]),
    ).resolves.toEqual([[], []]);
    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect(refreshCalls).toBe(1);
  });

  it("upgrades a public account through the CSRF-protected onboarding API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: {
          id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
          email: "viewer@cnsgroup.vn",
          roles: ["USER"],
          accountType: "INDIVIDUAL_APPLICANT",
        },
        meta: { request_id: "request-upgrade" },
      }),
    );

    await expect(
      authApi.upgradeToApplicant("INDIVIDUAL_APPLICANT"),
    ).resolves.toMatchObject({ accountType: "INDIVIDUAL_APPLICANT" });
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/applicant-upgrade");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(
      JSON.stringify({ accountType: "INDIVIDUAL_APPLICANT" }),
    );
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });
});

describe("affiliate API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("uses the privacy-safe affiliate history routes", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    for (const requestId of ["affiliate-referrals", "affiliate-commissions"]) {
      fetchMock.mockResolvedValueOnce(
        response({
          success: true,
          data: [],
          meta: { request_id: requestId },
        }),
      );
    }

    await affiliateApi.referrals();
    await affiliateApi.commissions();

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/affiliate/me/referrals?limit=50&offset=0",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/affiliate/me/commissions?limit=50",
    );
  });
});

describe("admin affiliate API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("maps profile, commission review, and rule actions to supported routes", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        response({
          success: true,
          data: {},
          meta: { request_id: "admin-affiliate" },
        }),
      );

    await adminAffiliateApi.profiles({
      search: "THV-ABC123",
      status: "SUSPENDED",
      offset: 50,
    });
    await adminAffiliateApi.suspend("user/1", "Confirmed policy abuse");
    await adminAffiliateApi.restore("user/1", "Appeal accepted after review");
    await adminAffiliateApi.commissions({
      status: "ON_HOLD",
      affiliateUserId: "affiliate-1",
    });
    await adminAffiliateApi.approveCommission("commission-1");
    await adminAffiliateApi.rejectCommission(
      "commission-2",
      "Invalid transaction source",
    );
    await adminAffiliateApi.reverseCommission(
      "commission-3",
      "Chargeback confirmed",
    );
    await adminAffiliateApi.commissionRules();
    await adminAffiliateApi.createCommissionRules({
      enabled: false,
      attributionWindowDays: 30,
      holdDays: 30,
      level2Enabled: false,
      level2RateBasisPoints: 0,
      rates: [{ serviceCode: "MEMBERSHIP", directRateBasisPoints: 500 }],
    });
    await adminAffiliateApi.publishCommissionRules("rule-1");
    await adminAffiliateApi.profileReferrals("user/1");
    await adminAffiliateApi.profileStatusHistory("user/1");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/admin/affiliate/profiles?limit=50&offset=50&search=THV-ABC123&status=SUSPENDED",
      "/api/v1/admin/affiliate/profiles/user%2F1/suspend",
      "/api/v1/admin/affiliate/profiles/user%2F1/restore",
      "/api/v1/admin/affiliate/commissions?limit=50&status=ON_HOLD&affiliateUserId=affiliate-1",
      "/api/v1/admin/affiliate/commissions/commission-1/approve",
      "/api/v1/admin/affiliate/commissions/commission-2/reject",
      "/api/v1/admin/affiliate/commissions/commission-3/reverse",
      "/api/v1/admin/affiliate/commission-rules",
      "/api/v1/admin/affiliate/commission-rules",
      "/api/v1/admin/affiliate/commission-rules/rule-1/publish",
      "/api/v1/admin/affiliate/profiles/user%2F1/referrals?limit=50&offset=0",
      "/api/v1/admin/affiliate/profiles/user%2F1/status-history?limit=50",
    ]);
    expect(fetchMock.mock.calls[1]?.[1]?.body).toBe(
      JSON.stringify({ reason: "Confirmed policy abuse" }),
    );
    expect(fetchMock.mock.calls[5]?.[1]?.body).toBe(
      JSON.stringify({ reason: "Invalid transaction source" }),
    );
    expect(fetchMock.mock.calls[8]?.[1]?.body).toBe(
      JSON.stringify({
        enabled: false,
        attributionWindowDays: 30,
        holdDays: 30,
        level2Enabled: false,
        level2RateBasisPoints: 0,
        rates: [{ serviceCode: "MEMBERSHIP", directRateBasisPoints: 500 }],
      }),
    );
  });
});

describe("account API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("uses the profile contract and CSRF header for updates", async () => {
    const profile = {
      userId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
      email: "owner@cnsgroup.vn",
      fullName: "Nguyễn Minh Anh",
      phone: "+84901234567",
      avatarMediaId: null,
      locale: "vi-VN",
      timezone: "Asia/Ho_Chi_Minh",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: profile,
        meta: { request_id: "profile-request" },
      }),
    );

    await expect(profileApi.update(profile)).resolves.toEqual(profile);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/users/me");
    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.method).toBe("PATCH");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("links an active avatar through the profile contract", async () => {
    const avatarMediaId = "2faacdd6-00fb-4164-907e-3e7d35f2490e";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: { avatarMediaId },
        meta: { request_id: "avatar-request" },
      }),
    );

    await profileApi.updateAvatar({ avatarMediaId });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/users/me");
    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(String(init?.body))).toEqual({ avatarMediaId });
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("uses the signed media upload contracts with CSRF protection", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        response({
          success: true,
          data: { mediaId: "media-id" },
          meta: { request_id: "signature-request" },
        }),
      )
      .mockResolvedValueOnce(
        response({
          success: true,
          data: { id: "media-id", status: "ACTIVE" },
          meta: { request_id: "completion-request" },
        }),
      );
    const intent = {
      confidentiality: "PRIVATE" as const,
      purpose: "AVATAR" as const,
      filename: "avatar.webp",
      mimeType: "image/webp",
      size: 1024,
    };
    const completion = {
      mediaId: "media-id",
      publicId: "users/user-id/avatar",
      version: 1,
      signature: "a".repeat(40),
    };

    await mediaApi.createUploadSignature(intent);
    await mediaApi.completeUpload(completion);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/media/upload-signature");
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/media/complete");
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual(
      intent,
    );
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual(
      completion,
    );
    expect(
      new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("csrf-value");
  });

  it("streams document bytes to English verification endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        response({
          success: true,
          data: { status: "MATCH", checkedAt: "2026-08-12T08:00:00Z" },
          meta: { request_id: "document-verification" },
        }),
      );
    const file = new File(["hello"], "proof.pdf", {
      type: "application/pdf",
    });

    await publicApi.verifyDocument("CNS-2026-0001", 0, file);
    await mediaApi.verifyDocument("media-id", file);

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/public/certificates/CNS-2026-0001/documents/0/verifications",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/media/media-id/verifications",
    );
    for (const [, init] of fetchMock.mock.calls) {
      expect(init?.method).toBe("POST");
      expect(init?.body).toBe(file);
      expect(new Headers(init?.headers).get("Content-Type")).toBe(
        "application/octet-stream",
      );
    }
    expect(
      new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("csrf-value");
  });

  it("preserves organization list pagination metadata", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: [],
        meta: {
          request_id: "organization-request",
          page: 2,
          pageSize: 10,
          total: 12,
        },
      }),
    );

    const result = await organizationApi.list(2, 10);

    expect(result.meta).toMatchObject({ page: 2, pageSize: 10, total: 12 });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/organizations?page=2&pageSize=10",
    );
  });

  it("does not send the immutable organization code in PATCH requests", async () => {
    const organization = {
      id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      code: "CNS-LAB",
      legalName: "Công ty TNHH CNS Lab",
      displayName: "CNS Lab",
      taxCode: "0312345678",
      status: "ACTIVE",
      ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
      currentRole: "OWNER",
      canManageMembers: true,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: organization,
        meta: { request_id: "organization-update" },
      }),
    );

    await organizationApi.update(organization.id, organization);

    const requestBody = fetchMock.mock.calls[0]?.[1]?.body;
    expect(JSON.parse(String(requestBody))).toEqual({
      legalName: organization.legalName,
      displayName: organization.displayName,
      taxCode: organization.taxCode,
    });
  });
});

describe("audit API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("serializes stable English audit filters", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: [],
        meta: { request_id: "audit-list", page: 2, pageSize: 25, total: 0 },
      }),
    );

    await auditApi.list({
      page: 2,
      pageSize: 25,
      action: "dossier.approved",
      resourceType: "dossier",
      resourceId: "dossier-1",
      createdFrom: "2026-08-01T00:00:00.000Z",
    });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("/api/v1/admin/audit?");
    expect(url).toContain("page=2");
    expect(url).toContain("action=dossier.approved");
    expect(url).toContain("resourceType=dossier");
    expect(url).toContain("resourceId=dossier-1");
    expect(url).not.toContain("quy-trinh");
  });

  it("uses CSRF protection for an integrity check", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: {
          scanned: 1,
          total: 1,
          isComplete: true,
          counts: {
            VERIFIED: 1,
            TAMPERED: 0,
            UNSEALED: 0,
            KEY_UNAVAILABLE: 0,
          },
        },
        meta: { request_id: "audit-check" },
      }),
    );

    await auditApi.checkIntegrity(250);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/admin/audit/integrity-checks?limit=250");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });
});

describe("staff account API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("lists staff accounts and sends CSRF-protected invitations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: [],
        meta: { request_id: "staff-list", page: 1, pageSize: 20, total: 0 },
      }),
    );

    await staffAccountsApi.list({ status: "SUSPENDED", query: "reviewer" });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/staff-accounts?page=1&pageSize=20&query=reviewer&status=SUSPENDED",
    );

    fetchMock.mockResolvedValueOnce(
      response({
        success: true,
        data: {
          id: "staff-1",
          email: "reviewer@cnsgroup.vn",
          role: "MODERATOR",
          status: "ACTIVE",
          createdAt: null,
          lastLoginAt: null,
        },
        meta: { request_id: "staff-create" },
      }),
    );
    await staffInvitationsApi.create({
      email: "reviewer@cnsgroup.vn",
      role: "MODERATOR",
    });
    expect(
      new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("csrf-value");

    const body = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));
    expect(body).toEqual({
      email: "reviewer@cnsgroup.vn",
      role: "MODERATOR",
    });
  });
});

describe("employee invitations API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("sends only an email; the server fixes the role to USER", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock.mockResolvedValueOnce(
      response({
        success: true,
        data: {
          id: "invite-1",
          email: "worker@example.com",
          role: "USER",
          status: "PENDING",
        },
        meta: { requestId: "invite-1" },
      }),
    );
    await employeeInvitationsApi.create("worker@example.com");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/admin/employee-invitations",
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      email: "worker@example.com",
    });
  });
});

describe("payroll API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("uses protected worksite-month routes without location payloads", async () => {
    const success = () =>
      response({
        success: true,
        data: [],
        meta: { request_id: "payroll-test", page: 1, pageSize: 20, total: 0 },
      });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(success())
      .mockResolvedValueOnce(success());

    await hrPayrollApi.listPeriods({
      pageSize: 20,
      worksiteId: "worksite/1",
      periodMonth: "2026-09-01",
    });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/hr/payroll-periods?page=1&pageSize=20&worksiteId=worksite%2F1&periodMonth=2026-09-01",
    );

    await hrPayrollApi.updateEntry("period/1", "entry/1", {
      allowance: "2000000",
      socialInsurance: "1890000",
      incomeTax: "700000",
    });
    const [url, init] = fetchMock.mock.calls[1] ?? [];
    expect(url).toBe(
      "/api/v1/admin/hr/payroll-periods/period%2F1/entries/entry%2F1",
    );
    expect(init?.method).toBe("PATCH");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
    expect(JSON.parse(String(init?.body))).toEqual({
      allowance: "2000000",
      socialInsurance: "1890000",
      incomeTax: "700000",
    });
  });
});

describe("HR dashboard API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the authenticated self endpoint without an employee identifier", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: { profileLinked: false },
        meta: { request_id: "hr-self-dashboard" },
      }),
    );
    await hrModeratorDashboardApi.summary();
    const [url, options] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/me/hr/dashboard-summary");
    expect(options?.credentials).toBe("include");
    expect(options?.body).toBeUndefined();
  });

  it("requests only the aggregate summary endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: {
          activeEmployeeCount: 8,
          attendancePendingCount: 2,
          locationExceptionPendingCount: 1,
          leavePendingCount: 3,
          overtimePendingCount: 4,
          payrollDraftCount: 1,
          updatedAt: "2026-09-23T08:00:00Z",
        },
        meta: { request_id: "hr-dashboard" },
      }),
    );

    await hrDashboardApi.summary();

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/hr/dashboard-summary",
    );
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      credentials: "include",
    });
    expect(fetchMock.mock.calls[0]?.[1]).not.toMatchObject({
      method: "POST",
      body: expect.anything(),
    });
  });
});

describe("HR Excel exports", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("downloads filtered reports with the authenticated session", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async () =>
        new Response("xlsx-data", {
          headers: {
            "Content-Type":
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          },
        }),
    );

    expect(
      await (await hrDepartmentApi.exportXlsx({ search: "Kỹ thuật" })).text(),
    ).toBe("xlsx-data");
    expect(
      await (
        await hrEmployeeApi.exportXlsx({
          search: "Minh",
          departmentId: "department/1",
          employmentStatus: "ACTIVE",
        })
      ).text(),
    ).toBe("xlsx-data");

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/hr/reports/departments.xlsx?search=K%E1%BB%B9+thu%E1%BA%ADt",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/admin/hr/reports/employees.xlsx?search=Minh&departmentId=department%2F1&employmentStatus=ACTIVE",
    );
    for (const [, options] of fetchMock.mock.calls) {
      expect(options).toMatchObject({
        credentials: "include",
        cache: "no-store",
      });
    }
  });

  it("uses the same filters for attendance, leave and overtime downloads", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => new Response("xlsx-data"));

    await hrAdminAttendanceApi.exportXlsx({
      departmentId: "department-1",
      status: "PENDING",
      workDateFrom: "2026-09-01",
      workDateTo: "2026-09-30",
    });
    await hrAdminLeaveApi.exportXlsx({
      search: "Minh",
      status: "APPROVED",
      startDateFrom: "2026-09-01",
    });
    await hrAdminOvertimeApi.exportXlsx({
      departmentId: "department-1",
      status: "APPROVED",
    });

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/admin/hr/reports/attendance.xlsx?departmentId=department-1&status=PENDING&workDateFrom=2026-09-01&workDateTo=2026-09-30",
      "/api/v1/admin/hr/reports/leave.xlsx?search=Minh&status=APPROVED&startDateFrom=2026-09-01",
      "/api/v1/admin/hr/reports/overtime.xlsx?departmentId=department-1&status=APPROVED",
    ]);
  });

  it("downloads filtered tasks and a selected payroll period privately", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => new Response("xlsx-data"));

    await taskAdminApi.exportXlsx({
      search: "Review",
      status: "IN_PROGRESS",
      priority: "HIGH",
    });
    await hrPayrollApi.exportXlsx("period/1");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/admin/hr/reports/tasks.xlsx?search=Review&status=IN_PROGRESS&priority=HIGH",
      "/api/v1/admin/hr/reports/payroll-periods/period%2F1/xlsx",
    ]);
    for (const [, options] of fetchMock.mock.calls) {
      expect(options).toMatchObject({
        credentials: "include",
        cache: "no-store",
      });
    }
  });
});
