import { canonicalSiteUrl, sitemapUrlSetXml, xmlResponse } from "@/lib/seo";

export function GET(): Response {
  const origin = canonicalSiteUrl();
  return xmlResponse(
    sitemapUrlSetXml(
      ["/", "/thu-vien", "/ban-do", "/kiem-tra"].map((path) => ({
        url: new URL(path, origin),
      })),
    ),
  );
}
