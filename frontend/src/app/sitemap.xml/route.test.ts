import { describe, expect, it, vi } from "vitest";

const sitemap = vi.hoisted(() => ({
  loadSitemapManifest: vi.fn(),
  loadCommunityPostSitemapManifest: vi.fn(),
  loadPublicGuideSitemapManifest: vi.fn(),
}));
vi.mock("@/lib/api/public-seo-server", () => ({
  loadSitemapManifest: sitemap.loadSitemapManifest,
}));
vi.mock("@/lib/api/community-sitemap-server", () => ({
  loadCommunityPostSitemapManifest: sitemap.loadCommunityPostSitemapManifest,
}));
vi.mock("@/lib/api/guide-seo-server", () => ({
  loadPublicGuideSitemapManifest: sitemap.loadPublicGuideSitemapManifest,
}));

import { GET } from "@/app/sitemap.xml/route";

describe("sitemap index", () => {
  it("includes paged public community sitemap routes", async () => {
    sitemap.loadSitemapManifest.mockResolvedValue({ pageCount: 1 });
    sitemap.loadCommunityPostSitemapManifest.mockResolvedValue({
      pageCount: 2,
    });
    sitemap.loadPublicGuideSitemapManifest.mockResolvedValue({ pageCount: 1 });

    const response = await GET();
    const xml = await response.text();

    expect(xml).toContain("/sitemaps/community/1.xml");
    expect(xml).toContain("/sitemaps/community/2.xml");
    expect(xml).toContain("/sitemaps/guides/1.xml");
    expect(xml).toContain("/sitemaps/works/1.xml");
  });

  it("omits community sitemap entries when its public feed is unavailable", async () => {
    sitemap.loadSitemapManifest.mockResolvedValue({ pageCount: 0 });
    sitemap.loadCommunityPostSitemapManifest.mockResolvedValue({
      pageCount: 0,
    });
    sitemap.loadPublicGuideSitemapManifest.mockResolvedValue({ pageCount: 0 });

    const xml = await (await GET()).text();

    expect(xml).not.toContain("/sitemaps/community/");
    expect(xml).not.toContain("/sitemaps/guides/");
    expect(xml).toContain("/sitemaps/static.xml");
  });
});
