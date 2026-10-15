import { loadCommunityPostSitemapPage } from "@/lib/api/community-sitemap-server";
import { canonicalSiteUrl, sitemapUrlSetXml, xmlResponse } from "@/lib/seo";

export async function GET(
  _request: Request,
  context: { params: Promise<{ page: string }> },
): Promise<Response> {
  const value = (await context.params).page.replace(/\.xml$/, "");
  const page = Number(value);
  const origin = canonicalSiteUrl();
  const slugs = await loadCommunityPostSitemapPage(page);
  return xmlResponse(
    sitemapUrlSetXml(
      slugs.map((slug) => ({
        url: new URL(`/community/posts/${encodeURIComponent(slug)}`, origin),
      })),
    ),
  );
}
