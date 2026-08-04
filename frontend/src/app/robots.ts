import type { MetadataRoute } from "next";

import { canonicalSiteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  const origin = canonicalSiteUrl();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/dashboard/", "/admin/"],
    },
    sitemap: new URL("/sitemap.xml", origin).href,
  };
}
