import { loadSitemapPage } from "@/lib/api/public-seo-server";
import { canonicalSiteUrl, sitemapUrlSetXml, xmlResponse } from "@/lib/seo";

export async function GET(
  _request: Request,
  context: { params: Promise<{ page: string }> },
): Promise<Response> {
  const value = (await context.params).page.replace(/\.xml$/, "");
  const page = Number(value);
  const origin = canonicalSiteUrl();
  const entries = await loadSitemapPage(page);
  return xmlResponse(
    sitemapUrlSetXml(
      entries.map((entry) => ({
        url: new URL(`/works/${encodeURIComponent(entry.slug)}`, origin),
        lastModified: entry.lastModified,
      })),
    ),
  );
}
