import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("@/lib/api/server-base-url", () => ({ resolveServerApiBaseUrl: () => "https://api.example.test" }));

import { loadCommunityPostSitemapManifest, loadCommunityPostSitemapPage } from "@/lib/api/community-sitemap-server";

describe("community sitemap data", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("derives sitemap count from anonymous public post pagination", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      success: true,
      data: [],
      meta: { requestId: "public-posts", page: 1, pageSize: 50, total: 101 },
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    expect(await loadCommunityPostSitemapManifest()).toEqual({ pageCount: 3 });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("https://api.example.test/api/v1/community/posts?page=1&pageSize=50&sort=recent");
  });

  it("returns no pages after API failure and never requests owner post statuses", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

    expect(await loadCommunityPostSitemapManifest()).toEqual({ pageCount: 0 });
    expect(await loadCommunityPostSitemapPage(1)).toEqual([]);
    expect(fetchMock.mock.calls.every(([url]) => String(url).includes("/api/v1/community/posts?"))).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/members/me/posts"))).toBe(false);
  });

  it("fails closed when the public page envelope has invalid pagination metadata", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      success: true,
      data: [{ slug: "public-post" }],
      meta: { requestId: "missing-total" },
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    expect(await loadCommunityPostSitemapManifest()).toEqual({ pageCount: 0 });
    expect(await loadCommunityPostSitemapPage(1)).toEqual([]);
  });

  it("rejects invalid sitemap page numbers without making an API request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");

    expect(await loadCommunityPostSitemapPage(0)).toEqual([]);
    expect(await loadCommunityPostSitemapPage(Number.NaN)).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
