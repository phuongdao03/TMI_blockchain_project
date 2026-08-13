import { describe, expect, it } from "vitest";

import {
  canonicalSiteUrl,
  escapeXml,
  sitemapIndexXml,
  sitemapUrlSetXml,
} from "@/lib/seo";

describe("public SEO output", () => {
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
