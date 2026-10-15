import { describe, expect, it, vi } from "vitest";

const sitemap = vi.hoisted(() => ({ loadCommunityPostSitemapPage: vi.fn() }));
vi.mock("@/lib/api/community-sitemap-server", () => sitemap);

import { GET } from "@/app/sitemaps/community/[page]/route";

describe("community sitemap pages", () => {
  it("emits public post canonical URLs from the public feed projection", async () => {
    sitemap.loadCommunityPostSitemapPage.mockResolvedValue([
      "lang-nghe-va-ky-uc",
      "gom-lang-co",
    ]);

    const response = await GET(
      new Request("https://example.test/sitemaps/community/1.xml"),
      { params: Promise.resolve({ page: "1.xml" }) },
    );
    const xml = await response.text();

    expect(xml).toContain(
      "http://localhost:3000/community/posts/lang-nghe-va-ky-uc",
    );
    expect(xml).toContain("http://localhost:3000/community/posts/gom-lang-co");
    expect(sitemap.loadCommunityPostSitemapPage).toHaveBeenCalledWith(1);
  });

  it("renders an empty URL set when the public page has no entries", async () => {
    sitemap.loadCommunityPostSitemapPage.mockResolvedValue([]);

    const xml = await (
      await GET(new Request("https://example.test/sitemaps/community/3.xml"), {
        params: Promise.resolve({ page: "3.xml" }),
      })
    ).text();

    expect(xml).toContain("<urlset");
    expect(xml).not.toContain("<url>");
  });
});
