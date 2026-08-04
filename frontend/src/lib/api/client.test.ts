import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  authApi,
  mediaApi,
  organizationApi,
  profileApi,
  rankingApi,
} from "@/lib/api/client";

function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("auth API client", () => {
  beforeEach(() => {
    document.cookie = "tmi_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("rotates once on an expired access cookie and retries /me", async () => {
    const user = {
      id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
      email: "owner@tmigroup.vn",
      roles: ["APPLICANT"],
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
    document.cookie = "tmi_csrf=; Max-Age=0; Path=/";
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
});

describe("account API client", () => {
  beforeEach(() => {
    document.cookie = "tmi_csrf=csrf-value";
    vi.restoreAllMocks();
  });

  it("uses the profile contract and CSRF header for updates", async () => {
    const profile = {
      userId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
      email: "owner@tmigroup.vn",
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
      code: "TMI-LAB",
      legalName: "Công ty TNHH TMI Lab",
      displayName: "TMI Lab",
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

describe("ranking API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("requests the public snapshot with stable filters", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        success: true,
        data: { snapshot: {}, items: [], pagination: { page: 2, pageSize: 10, total: 0 } },
        meta: { request_id: "ranking-request" },
      }),
    );

    await rankingApi.public("heritage campaign", { page: 2, pageSize: 10, version: 3, categoryId: "category-1" });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/public/campaigns/heritage%20campaign/ranking?page=2&pageSize=10&version=3&categoryId=category-1",
    );
  });
});
