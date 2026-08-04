import { loadSitemapManifest } from "@/lib/api/public-seo-server";
import { canonicalSiteUrl, sitemapIndexXml, xmlResponse } from "@/lib/seo";

export async function GET(): Promise<Response> {
  const origin = canonicalSiteUrl();
  const manifest = await loadSitemapManifest();
  const urls = [new URL("/sitemaps/static.xml", origin)];
  for (let page = 1; page <= manifest.pageCount; page += 1) {
    urls.push(new URL(`/sitemaps/works/${page}.xml`, origin));
  }
  return xmlResponse(sitemapIndexXml(urls));
}
