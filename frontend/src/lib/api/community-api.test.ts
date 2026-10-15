import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  communityAdminApi,
  communityApi,
  communityMemberApi,
} from "@/lib/api/client";

describe("community API client", () => {
  beforeEach(() => {
    document.cookie = "cns_csrf=community-csrf";
    vi.restoreAllMocks();
  });

  it("loads categories and filters the paginated feed by category", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: [],
        meta: { requestId: "community-feed", page: 2, pageSize: 20, total: 0 },
      })),
    );

    await communityApi.categories();
    await communityApi.posts({ page: 2, category: "heritage-culture" });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/community/categories");
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/community/posts?page=2&pageSize=20&category=heritage-culture",
    );
  });

  it("serializes all discovery filters without losing pagination", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: [],
        meta: { requestId: "community-discovery", page: 3, pageSize: 25, total: 0 },
      })),
    );

    await communityApi.posts({
      page: 3,
      pageSize: 25,
      category: "heritage-culture",
      tag: "dong-ho",
      relatedWorkId: "work-1",
      q: "  tranh Đông Hồ  ",
      sort: "discussed",
    });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/community/posts?page=3&pageSize=25&category=heritage-culture&tag=dong-ho&relatedWorkId=work-1&q=tranh+%C4%90%C3%B4ng+H%E1%BB%93&sort=discussed",
    );
  });

  it("writes community tag labels and reads owner posts with optional status", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: [],
        meta: { requestId: "community-owner", page: 2, pageSize: 25, total: 0 },
      })),
    );
    const input = {
      title: "Bài viết",
      content: "Nội dung",
      categoryId: "category-1",
      tags: ["Di sản", "Tranh Đông Hồ"],
    };

    await communityApi.createPost(input);
    await communityMemberApi.myPosts({ status: "REJECTED", page: 2, pageSize: 25 });
    await communityMemberApi.myPost("post/1");

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(input),
    });
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/community/members/me/posts?status=REJECTED&page=2&pageSize=25",
    );
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "/api/v1/community/members/me/posts/post%2F1",
    );
  });

  it("reads post slugs as path segments and preserves ordered image IDs in draft input", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: { id: "post-1", slug: "a/b", title: "Bài viết" },
        meta: { requestId: "community-write" },
      })),
    );
    const input = {
      title: "Bài viết",
      content: "Nội dung\nkhông phải HTML",
      categoryId: "category-1",
      imageMediaIds: ["image-second", "image-first"],
    };

    await communityApi.post("a/b");
    await communityApi.createPost(input);

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/community/posts/a%2Fb",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/community/posts");
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(input),
    });
    expect(
      new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token"),
    ).toBe("community-csrf");
  });

  it("updates and submits drafts through the authenticated mutation contract", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: { id: "post/2", status: "PENDING" },
        meta: { requestId: "community-submit" },
      })),
    );
    const input = {
      title: "Tiêu đề",
      content: "Nội dung",
      categoryId: "category-1",
    };

    await communityApi.updatePost("post/2", input);
    await communityApi.submitPost("post/2");

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/community/posts/post%2F2",
    );
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      method: "PATCH",
      body: JSON.stringify(input),
    });
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/community/posts/post%2F2/submit",
    );
    for (const [, init] of fetchMock.mock.calls) {
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(
        "community-csrf",
      );
    }
  });

  it("soft-deletes an owned post through the CSRF protected API helper", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));

    await communityApi.deletePost("post/1");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/community/posts/post%2F1");
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: "DELETE" });
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("X-CSRF-Token")).toBe("community-csrf");
  });

  it("loads the pending queue and requires reasons for publish and reject", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      Promise.resolve(response({
        success: true,
        data: [],
        meta: { requestId: "community-queue", page: 1, pageSize: 20, total: 0 },
      })),
    );

    await communityAdminApi.pendingPosts(3);
    await communityAdminApi.publishPost("post/3", { reason: "Đúng tiêu chí" });
    await communityAdminApi.rejectPost("post-4", { reason: "Thiếu nguồn" });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/admin/community/posts?status=PENDING&page=3&pageSize=20",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/admin/community/posts/post%2F3/publish",
    );
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ reason: "Đúng tiêu chí" }),
    });
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "/api/v1/admin/community/posts/post-4/reject",
    );
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ reason: "Thiếu nguồn" }),
    });
  });
});

function response(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  });
}
