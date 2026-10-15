import { beforeEach, describe, expect, it, vi } from "vitest";

import { communityAdminApi } from "@/lib/api/client";

describe("community COM012 admin API", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=community-csrf";
    vi.restoreAllMocks();
  });

  it("searches paginated post/comment workspaces with the documented filters", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => Promise.resolve(pageResponse()));

    await communityAdminApi.workspacePosts({
      q: "thợ gốm",
      status: "HIDDEN",
      page: 2,
      pageSize: 30,
    });
    await communityAdminApi.workspaceComments({
      q: "bình luận",
      postId: "post/1",
      authorUsername: "lan-anh",
      visibility: "DELETED",
      page: 3,
    });
    await communityAdminApi.members({ q: "lan", page: 4, pageSize: 25 });
    await communityAdminApi.memberRestrictions("member/1", 2);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/admin/community/posts?page=2&pageSize=30&q=th%E1%BB%A3+g%E1%BB%91m&status=HIDDEN",
      "/api/v1/admin/community/comments?page=3&pageSize=20&q=b%C3%ACnh+lu%E1%BA%ADn&postId=post%2F1&authorUsername=lan-anh&visibility=DELETED",
      "/api/v1/admin/community/members?page=4&pageSize=25&q=lan",
      "/api/v1/admin/community/members/member%2F1/restrictions?page=2&pageSize=20",
    ]);
  });

  it("sends CSRF-protected post, comment, and restriction moderation actions", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => Promise.resolve(successResponse({})));
    const reason = { reason: "Đã xem xét nội dung." };

    await communityAdminApi.pinPost("post/1", reason);
    await communityAdminApi.unpinPost("post/1", reason);
    await communityAdminApi.lockPostComments("post/1", reason);
    await communityAdminApi.unlockPostComments("post/1", reason);
    await communityAdminApi.deleteWorkspacePost("post/1", reason);
    await communityAdminApi.restoreWorkspacePost("post/1", reason);
    await communityAdminApi.hideWorkspaceComment("comment/1", reason);
    await communityAdminApi.restoreWorkspaceComment("comment/1", reason);
    await communityAdminApi.deleteWorkspaceComment("comment/1", reason);
    await communityAdminApi.createMemberRestriction("member/1", {
      scope: "COMMENTS",
      durationMinutes: 60,
      reason: "Cần rà soát thêm.",
    });
    await communityAdminApi.revokeMemberRestriction(
      "member/1",
      "restriction/1",
      reason,
    );

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/admin/community/posts/post%2F1/pin", "POST"],
      ["/api/v1/admin/community/posts/post%2F1/unpin", "POST"],
      ["/api/v1/admin/community/posts/post%2F1/comments/lock", "POST"],
      ["/api/v1/admin/community/posts/post%2F1/comments/unlock", "POST"],
      ["/api/v1/admin/community/posts/post%2F1", "DELETE"],
      ["/api/v1/admin/community/posts/post%2F1/restore", "POST"],
      ["/api/v1/admin/community/comments/comment%2F1/hide", "POST"],
      ["/api/v1/admin/community/comments/comment%2F1/restore", "POST"],
      ["/api/v1/admin/community/comments/comment%2F1/delete", "POST"],
      ["/api/v1/admin/community/members/member%2F1/restrictions", "POST"],
      [
        "/api/v1/admin/community/members/member%2F1/restrictions/restriction%2F1",
        "DELETE",
      ],
    ]);
    expect(fetchMock.mock.calls[4]?.[1]?.body).toBe(JSON.stringify(reason));
    expect(fetchMock.mock.calls[8]?.[1]?.body).toBe(JSON.stringify(reason));
    for (const [, init] of fetchMock.mock.calls) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });
});

function pageResponse() {
  return new Response(
    JSON.stringify({
      success: true,
      data: [],
      meta: { requestId: "admin", page: 1, pageSize: 20, total: 0 },
    }),
    {
      headers: { "Content-Type": "application/json" },
    },
  );
}

function successResponse(data: unknown) {
  return new Response(
    JSON.stringify({ success: true, data, meta: { requestId: "admin" } }),
    {
      headers: { "Content-Type": "application/json" },
    },
  );
}
