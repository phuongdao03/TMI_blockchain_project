import "server-only";

import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";

const COMMUNITY_SITEMAP_PAGE_SIZE = 50;
const MAX_COMMUNITY_SITEMAP_PAGES = 1_000;

export async function loadCommunityPostSitemapManifest(): Promise<{
  pageCount: number;
}> {
  const firstPage = await loadPublicCommunityPage(1);
  if (!firstPage) return { pageCount: 0 };
  const total = Number.isFinite(firstPage.meta.total)
    ? Math.max(0, firstPage.meta.total)
    : 0;
  const pageCount = Math.ceil(total / COMMUNITY_SITEMAP_PAGE_SIZE);
  return { pageCount: Math.min(pageCount, MAX_COMMUNITY_SITEMAP_PAGES) };
}

export async function loadCommunityPostSitemapPage(
  page: number,
): Promise<string[]> {
  if (
    !Number.isSafeInteger(page) ||
    page < 1 ||
    page > MAX_COMMUNITY_SITEMAP_PAGES
  )
    return [];
  const result = await loadPublicCommunityPage(page);
  return (
    result?.data.flatMap((post) => (post.slug.trim() ? [post.slug] : [])) ?? []
  );
}

interface PublicCommunitySitemapPage {
  data: { slug: string }[];
  meta: { total: number };
}

async function loadPublicCommunityPage(
  page: number,
): Promise<PublicCommunitySitemapPage | null> {
  const parameters = new URLSearchParams({
    page: String(page),
    pageSize: String(COMMUNITY_SITEMAP_PAGE_SIZE),
    sort: "recent",
  });
  try {
    const response = await fetch(
      `${resolveServerApiBaseUrl()}/api/v1/community/posts?${parameters.toString()}`,
      { cache: "no-store" },
    );
    if (!response.ok) return null;
    const payload: unknown = await response.json();
    if (!isPublicCommunitySitemapEnvelope(payload)) return null;
    return { data: payload.data, meta: { total: payload.meta.total } };
  } catch {
    return null;
  }
}

function isPublicCommunitySitemapEnvelope(value: unknown): value is {
  success: true;
  data: { slug: string }[];
  meta: { total: number };
} {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  const meta = payload.meta;
  return (
    payload.success === true &&
    Array.isArray(payload.data) &&
    payload.data.every(
      (post) =>
        Boolean(post) &&
        typeof post === "object" &&
        typeof (post as Record<string, unknown>).slug === "string",
    ) &&
    Boolean(meta) &&
    typeof meta === "object" &&
    typeof (meta as Record<string, unknown>).total === "number" &&
    Number.isFinite((meta as Record<string, unknown>).total)
  );
}
