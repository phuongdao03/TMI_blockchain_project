import "server-only";

import type { SuccessEnvelope } from "@/lib/api/types";
import type { SitemapEntry } from "@/lib/seo";

export type SitemapManifest = {
  generation: string;
  total: number;
  pageSize: number;
  pageCount: number;
  generatedAt: string;
};

export async function loadSitemapManifest(): Promise<SitemapManifest> {
  return loadSeo<SitemapManifest>("/api/v1/public/seo/sitemap", {
    generation: "unavailable",
    total: 0,
    pageSize: 10_000,
    pageCount: 0,
    generatedAt: new Date(0).toISOString(),
  });
}

export async function loadSitemapPage(page: number): Promise<SitemapEntry[]> {
  if (!Number.isSafeInteger(page) || page < 1) return [];
  return loadSeo<SitemapEntry[]>(`/api/v1/public/seo/sitemap/${page}`, []);
}

async function loadSeo<Data>(path: string, fallback: Data): Promise<Data> {
  const apiBaseUrl = process.env.API_BASE_URL;
  if (!apiBaseUrl) return fallback;
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    const payload = (await response.json()) as SuccessEnvelope<Data>;
    return payload.success ? payload.data : fallback;
  } catch {
    return fallback;
  }
}
