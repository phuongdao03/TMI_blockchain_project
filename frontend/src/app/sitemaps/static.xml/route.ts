import { canonicalSiteUrl, sitemapUrlSetXml, xmlResponse } from "@/lib/seo";

export function GET(): Response {
  const origin = canonicalSiteUrl();
  return xmlResponse(
    sitemapUrlSetXml(
      ["/", "/works", "/verify"].map((path) => ({
        url: new URL(path, origin),
      })),
    ),
  );
}
