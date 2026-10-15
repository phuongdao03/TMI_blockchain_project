import { beforeEach, describe, expect, it, vi } from "vitest";

import { communityApi, communityMemberApi } from "@/lib/api/client";

describe("community interaction API client", () => {
  it("edits and soft-deletes an owned comment with CSRF protection", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        response({
          success: true,
          data: { id: "comment/1", content: "Đã sửa" },
          meta: { requestId: "edit" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await communityApi.updateComment("comment/1", { content: "Đã sửa" });
    await communityApi.deleteComment("comment/1");

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/community/comments/comment%2F1", "PATCH"],
      ["/api/v1/community/comments/comment%2F1", "DELETE"],
    ]);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      body: JSON.stringify({ content: "Đã sửa" }),
    });
    for (const [, init] of fetchMock.mock.calls) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });

  beforeEach(() => {
    document.cookie = "cns_csrf=community-csrf";
    vi.restoreAllMocks();
  });

  it("loads paginated top-level comment threads and creates comments or replies", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(response({ success: true, data: [], meta: pageMeta })),
      );

    await communityApi.comments("post/1", 2);
    await communityApi.createComment("post/1", {
      content: "Một chia sẻ hữu ích",
    });
    await communityApi.createComment("post/1", {
      content: "Cảm ơn bạn",
      parentId: "comment/1",
    });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/community/posts/post%2F1/comments?page=2&pageSize=20",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/community/posts/post%2F1/comments",
    );
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ content: "Một chia sẻ hữu ích" }),
    });
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ content: "Cảm ơn bạn", parentId: "comment/1" }),
    });
    for (const [, init] of fetchMock.mock.calls.slice(1)) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });

  it("uses idempotent like and bookmark methods with the session CSRF token", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(
          response({ success: true, data: {}, meta: { requestId: "r" } }),
        ),
      );

    await communityApi.likePost("post/2");
    await communityApi.unlikePost("post/2");
    await communityApi.bookmarkPost("post/2");
    await communityApi.unbookmarkPost("post/2");

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/community/posts/post%2F2/like", "PUT"],
      ["/api/v1/community/posts/post%2F2/like", "DELETE"],
      ["/api/v1/community/posts/post%2F2/bookmark", "PUT"],
      ["/api/v1/community/posts/post%2F2/bookmark", "DELETE"],
    ]);
    for (const [, init] of fetchMock.mock.calls) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });

  it("loads private bookmarks and public member profile/posts by username", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(response({ success: true, data: [], meta: pageMeta })),
      );

    await communityMemberApi.bookmarks(3);
    await communityMemberApi.profile("nguyen/an");
    await communityMemberApi.posts("nguyen/an", 4);
    await communityMemberApi.follow("member/1");
    await communityMemberApi.unfollow("member/1");

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/members/me/bookmarks?page=3&pageSize=20", undefined],
      ["/api/v1/members/nguyen%2Fan", undefined],
      ["/api/v1/members/nguyen%2Fan/posts?page=4&pageSize=20", undefined],
      ["/api/v1/members/member%2F1/follow", "PUT"],
      ["/api/v1/members/member%2F1/follow", "DELETE"],
    ]);
    for (const [, init] of fetchMock.mock.calls.slice(3)) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });

  it("updates only community profile fields and loads paginated follower lists", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(response({ success: true, data: [], meta: pageMeta })),
      );
    const input = {
      username: "lan_anh",
      displayName: "Lan Anh",
      avatarUrl: null,
      bio: "Ghi chép",
    };

    await communityMemberApi.updateProfile(input);
    await communityMemberApi.followers("lan-anh", 2);
    await communityMemberApi.following("lan-anh", 3);

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      ["/api/v1/community/members/me", "PATCH"],
      [
        "/api/v1/community/members/lan-anh/followers?page=2&pageSize=20",
        undefined,
      ],
      [
        "/api/v1/community/members/lan-anh/following?page=3&pageSize=20",
        undefined,
      ],
    ]);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      body: JSON.stringify(input),
    });
    expect(
      new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("community-csrf");
  });

  it("sorts comments and supports comment likes and deduplicated post views", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        Promise.resolve(response({ success: true, data: [], meta: pageMeta })),
      );

    await communityApi.comments("post/1", 2, undefined, "newest");
    await communityApi.likeComment("comment/1");
    await communityApi.unlikeComment("comment/1");
    await communityApi.recordPostView("post/1");

    expect(
      fetchMock.mock.calls.map(([url, init]) => [url, init?.method]),
    ).toEqual([
      [
        "/api/v1/community/posts/post%2F1/comments?page=2&pageSize=20&sort=newest",
        undefined,
      ],
      ["/api/v1/community/comments/comment%2F1/like", "PUT"],
      ["/api/v1/community/comments/comment%2F1/like", "DELETE"],
      ["/api/v1/community/posts/post%2F1/views", "POST"],
    ]);
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({ method: "PUT" });
    expect(fetchMock.mock.calls[3]?.[1]).toMatchObject({ method: "POST" });
    expect(fetchMock.mock.calls[3]?.[1]?.body).toBeUndefined();
    for (const [, init] of fetchMock.mock.calls.slice(1)) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });
});

const pageMeta = {
  requestId: "community-interactions",
  page: 1,
  pageSize: 20,
  total: 0,
};

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  });
}
