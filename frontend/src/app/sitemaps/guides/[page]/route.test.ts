import { describe, expect, it, vi } from "vitest";

const sitemap = vi.hoisted(() => ({ loadPublicGuideSitemapEntries: vi.fn() }));
vi.mock("@/lib/api/guide-seo-server", () => sitemap);

import { GET } from "@/app/sitemaps/guides/[page]/route";

describe("guide sitemap pages", () => {
  it("emits canonical public guide URLs and modified dates", async () => {
    sitemap.loadPublicGuideSitemapEntries.mockResolvedValue([
      { slug: "explore-nominations", lastModified: "2026-10-18T00:00:00Z" },
    ]);
    const response = await GET(
      new Request("https://example.test/sitemaps/guides/1.xml"),
      { params: Promise.resolve({ page: "1.xml" }) },
    );
    const xml = await response.text();

    expect(xml).toContain("/guide/explore-nominations");
    expect(xml).toContain("<lastmod>2026-10-18T00:00:00Z</lastmod>");
    expect(sitemap.loadPublicGuideSitemapEntries).toHaveBeenCalledWith(1);
  });
});
