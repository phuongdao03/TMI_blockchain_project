export type SitemapEntry = {
  slug: string;
  lastModified: string;
};

export function canonicalSiteUrl(
  value = process.env.NEXT_PUBLIC_APP_BASE_URL ?? process.env.APP_BASE_URL,
): URL {
  try {
    const url = new URL(value ?? "http://localhost:3000");
    if (!["http:", "https:"].includes(url.protocol))
      throw new Error("protocol");
    return new URL(url.origin);
  } catch {
    return new URL("http://localhost:3000");
  }
}

export function escapeXml(value: string): string {
  return value.replace(/[<>&"']/g, (character) => {
    const entities: Record<string, string> = {
      "<": "&lt;",
      ">": "&gt;",
      "&": "&amp;",
      '"': "&quot;",
      "'": "&apos;",
    };
    return entities[character] ?? character;
  });
}

export function sitemapIndexXml(urls: URL[]): string {
  return xmlDocument(
    `<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls
      .map((url) => `<sitemap><loc>${escapeXml(url.href)}</loc></sitemap>`)
      .join("")}</sitemapindex>`,
  );
}

export function sitemapUrlSetXml(
  entries: Array<{ url: URL; lastModified?: string }>,
): string {
  return xmlDocument(
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries
      .map(
        ({ url, lastModified }) =>
          `<url><loc>${escapeXml(url.href)}</loc>${
            lastModified ? `<lastmod>${escapeXml(lastModified)}</lastmod>` : ""
          }</url>`,
      )
      .join("")}</urlset>`,
  );
}

export function xmlResponse(body: string): Response {
  return new Response(body, {
    headers: {
      "Cache-Control":
        "public, max-age=0, s-maxage=300, stale-while-revalidate=60",
      "Content-Type": "application/xml; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function xmlDocument(body: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?>${body}`;
}
