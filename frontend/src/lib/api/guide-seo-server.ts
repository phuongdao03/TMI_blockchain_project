import "server-only";

import type { CmsGuideArticle } from "@/lib/api/types";
import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";
import type { SitemapEntry } from "@/lib/seo";

const GUIDE_SITEMAP_PAGE_SIZE = 100;
const MAX_GUIDE_SITEMAP_PAGES = 1_000;

export async function loadPublicGuideArticle(
  slug: string,
): Promise<CmsGuideArticle | null> {
  try {
    const response = await fetch(
      `${resolveServerApiBaseUrl()}/api/v1/public/guide/articles/${encodeURIComponent(slug)}`,
      { cache: "no-store" },
    );
    if (!response.ok) return null;
    const payload = (await response.json()) as {
      success?: boolean;
      data?: CmsGuideArticle;
    };
    return payload.success && payload.data ? payload.data : null;
  } catch {
    return null;
  }
}

export async function loadPublicGuideSitemapManifest(): Promise<{
  pageCount: number;
}> {
  const result = await loadPublicGuideSitemapPage(1);
  const pageCount = result
    ? Math.ceil(result.total / GUIDE_SITEMAP_PAGE_SIZE)
    : 0;
  return { pageCount: Math.min(pageCount, MAX_GUIDE_SITEMAP_PAGES) };
}

export async function loadPublicGuideSitemapPage(
  page: number,
): Promise<{ entries: SitemapEntry[]; total: number } | null> {
  if (
    !Number.isSafeInteger(page) ||
    page < 1 ||
    page > MAX_GUIDE_SITEMAP_PAGES
  ) {
    return null;
  }
  const parameters = new URLSearchParams({
    page: String(page),
    pageSize: String(GUIDE_SITEMAP_PAGE_SIZE),
  });
  try {
    const response = await fetch(
      `${resolveServerApiBaseUrl()}/api/v1/public/guide/articles?${parameters.toString()}`,
      { cache: "no-store" },
    );
    if (!response.ok) return null;
    const payload: unknown = await response.json();
    if (!isGuideSitemapPage(payload)) return null;
    return {
      entries: payload.data.flatMap((article) =>
        article.slug.trim()
          ? [{ slug: article.slug, lastModified: article.updatedAt }]
          : [],
      ),
      total: payload.meta.total,
    };
  } catch {
    return null;
  }
}

export async function loadPublicGuideSitemapEntries(
  page: number,
): Promise<SitemapEntry[]> {
  return (await loadPublicGuideSitemapPage(page))?.entries ?? [];
}

interface GuideSitemapPage {
  data: Array<{ slug: string; updatedAt: string }>;
  meta: { total: number };
}

function isGuideSitemapPage(value: unknown): value is GuideSitemapPage {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  const meta = payload.meta;
  return (
    payload.success === true &&
    Array.isArray(payload.data) &&
    payload.data.every(
      (article) =>
        Boolean(article) &&
        typeof article === "object" &&
        typeof (article as Record<string, unknown>).slug === "string" &&
        typeof (article as Record<string, unknown>).updatedAt === "string",
    ) &&
    Boolean(meta) &&
    typeof meta === "object" &&
    typeof (meta as Record<string, unknown>).total === "number" &&
    Number.isFinite((meta as Record<string, unknown>).total)
  );
}
