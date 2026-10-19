import { loadPublicGuideSitemapEntries } from "@/lib/api/guide-seo-server";
import { canonicalSiteUrl, sitemapUrlSetXml, xmlResponse } from "@/lib/seo";

export async function GET(
  _request: Request,
  context: { params: Promise<{ page: string }> },
): Promise<Response> {
  const value = (await context.params).page.replace(/\.xml$/, "");
  const page = Number(value);
  const origin = canonicalSiteUrl();
  const entries = await loadPublicGuideSitemapEntries(page);
  return xmlResponse(
    sitemapUrlSetXml(
      entries.map(({ slug, lastModified }) => ({
        url: new URL(`/guide/${encodeURIComponent(slug)}`, origin),
        lastModified,
      })),
    ),
  );
}
