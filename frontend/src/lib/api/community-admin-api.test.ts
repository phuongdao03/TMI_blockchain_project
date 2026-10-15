import { beforeEach, describe, expect, it, vi } from "vitest";

import { communityAdminApi, communityReportApi } from "@/lib/api/client";

describe("community reports and administration API", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=admin-csrf";
    vi.restoreAllMocks();
  });

  it("submits post and comment reports with the contract reason and details", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(
          response({ success: true, data: {}, meta: { requestId: "report" } }),
        ),
      );

    await communityReportApi.reportPost("post/1", {
      reason: "SPAM",
      details: "Lặp lại đường dẫn quảng cáo.",
    });
    await communityReportApi.reportComment("comment/1", {
      reason: "HARASSMENT",
    });

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/community/posts/post%2F1/reports", "POST"],
      ["/api/v1/community/comments/comment%2F1/reports", "POST"],
    ]);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      body: JSON.stringify({
        reason: "SPAM",
        details: "Lặp lại đường dẫn quảng cáo.",
      }),
    });
    for (const [, init] of fetchMock.mock.calls) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("admin-csrf");
    }
  });

  it("loads and resolves reports and uses explicit post/comment visibility routes", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(response({ success: true, data: [], meta: pageMeta })),
      );
    const reason = "Vi phạm quy định cộng đồng.";

    const reportRequest = new AbortController();
    await communityAdminApi.reports(
      { page: 2, pageSize: 30 },
      reportRequest.signal,
    );
    await communityAdminApi.resolveReport("report/1", {
      action: "HIDE",
      reason,
    });
    await communityAdminApi.hidePost("post/1", { reason });
    await communityAdminApi.restorePost("post/1", { reason });
    await communityAdminApi.hideComment("comment/1", { reason });
    await communityAdminApi.restoreComment("comment/1", { reason });

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      [
        "/api/v1/admin/community/reports?status=OPEN&page=2&pageSize=30",
        undefined,
      ],
      ["/api/v1/admin/community/reports/report%2F1/resolve", "POST"],
      ["/api/v1/admin/community/posts/post%2F1/hide", "POST"],
      ["/api/v1/admin/community/posts/post%2F1/restore", "POST"],
      ["/api/v1/admin/community/comments/comment%2F1/hide", "POST"],
      ["/api/v1/admin/community/comments/comment%2F1/restore", "POST"],
    ]);
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(reportRequest.signal);
    for (const [, init] of fetchMock.mock.calls.slice(1)) {
      expect(init?.body).toBe(
        JSON.stringify(
          init?.body === JSON.stringify({ action: "HIDE", reason })
            ? { action: "HIDE", reason }
            : { reason },
        ),
      );
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("admin-csrf");
    }
  });

  it("filters moderation history and manages categories and pre-moderation settings", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(
          response({ success: true, data: {}, meta: { requestId: "admin" } }),
        ),
      );

    await communityAdminApi.moderationHistory({
      targetType: "COMMENT",
      targetId: "comment/1",
      page: 3,
    });
    await communityAdminApi.categories();
    await communityAdminApi.createCategory({
      name: "Chuyện làng",
      slug: "chuyen-lang",
      description: "Góc chuyện làng.",
      reason: "Mở chuyên mục mới.",
    });
    await communityAdminApi.updateCategory("category/1", {
      isActive: false,
      reason: "Tạm ngừng chuyên mục.",
    });
    await communityAdminApi.settings();
    await communityAdminApi.updateSettings({
      preModerationEnabled: false,
      reason: "Đã hoàn tất giai đoạn kiểm duyệt thử nghiệm.",
    });

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      [
        "/api/v1/admin/community/moderation-history?targetType=COMMENT&targetId=comment%2F1&page=3&pageSize=20",
        undefined,
      ],
      ["/api/v1/admin/community/categories", undefined],
      ["/api/v1/admin/community/categories", "POST"],
      ["/api/v1/admin/community/categories/category%2F1", "PATCH"],
      ["/api/v1/admin/community/settings", undefined],
      ["/api/v1/admin/community/settings", "PUT"],
    ]);
    for (const [, init] of fetchMock.mock.calls.filter(
      ([, init]) => init?.method,
    )) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("admin-csrf");
    }
  });
});

const pageMeta = {
  requestId: "community-admin",
  page: 1,
  pageSize: 20,
  total: 0,
};

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  });
}
