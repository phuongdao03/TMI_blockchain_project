import { loadSitemapManifest } from "@/lib/api/public-seo-server";
import { loadCommunityPostSitemapManifest } from "@/lib/api/community-sitemap-server";
import { loadPublicGuideSitemapManifest } from "@/lib/api/guide-seo-server";
import { canonicalSiteUrl, sitemapIndexXml, xmlResponse } from "@/lib/seo";

export async function GET(): Promise<Response> {
  const origin = canonicalSiteUrl();
  const [manifest, communityManifest, guideManifest] = await Promise.all([
    loadSitemapManifest(),
    loadCommunityPostSitemapManifest(),
    loadPublicGuideSitemapManifest(),
  ]);
  const urls = [new URL("/sitemaps/static.xml", origin)];
  for (let page = 1; page <= manifest.pageCount; page += 1) {
    urls.push(new URL(`/sitemaps/works/${page}.xml`, origin));
  }
  for (let page = 1; page <= communityManifest.pageCount; page += 1) {
    urls.push(new URL(`/sitemaps/community/${page}.xml`, origin));
  }
  for (let page = 1; page <= guideManifest.pageCount; page += 1) {
    urls.push(new URL(`/sitemaps/guides/${page}.xml`, origin));
  }
  return xmlResponse(sitemapIndexXml(urls));
}
