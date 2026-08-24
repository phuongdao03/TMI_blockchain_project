import { afterEach, describe, expect, it, vi } from "vitest";

import {
  canonicalSiteUrl,
  escapeXml,
  sitemapIndexXml,
  sitemapUrlSetXml,
} from "@/lib/seo";

describe("public SEO output", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("uses the public build origin for generated metadata and sitemap routes", () => {
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    vi.stubEnv("APP_BASE_URL", "http://backend:8000");

    expect(canonicalSiteUrl().href).toBe("https://decu.tinhhoaviet.org.vn/");
  });

  it("uses only a validated canonical origin", () => {
    expect(canonicalSiteUrl("https://catalog.tmi.vn/path?q=1").href).toBe(
      "https://catalog.tmi.vn/",
    );
    expect(canonicalSiteUrl("javascript:alert(1)").href).toBe(
      "http://localhost:3000/",
    );
  });

  it("escapes special characters in XML values", () => {
    expect(escapeXml(`<asset title="A&B">'`)).toBe(
      "&lt;asset title=&quot;A&amp;B&quot;&gt;&apos;",
    );
    const sitemap = sitemapUrlSetXml([
      { url: new URL("https://tmi.vn/works/a?x=1&y=2") },
    ]);
    expect(sitemap).toContain("x=1&amp;y=2");
    expect(sitemap).not.toContain("x=1&y=2");
  });

  it("creates a sitemap index without injecting unescaped URLs", () => {
    const xml = sitemapIndexXml([
      new URL("https://tmi.vn/sitemaps/works/1.xml?x=1&y=2"),
    ]);
    expect(xml).toContain("?x=1&amp;y=2");
    expect(xml).toContain("<sitemapindex");
  });
});
