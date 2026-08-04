import "server-only";

import type {
  PublicCatalogFilters,
  PublicCatalogInitialData,
  PublicCatalogPage,
  PublicCatalogWork,
  SuccessEnvelope,
} from "@/lib/api/types";

export async function loadPublicCatalogInitialData(
  filters: PublicCatalogFilters,
): Promise<PublicCatalogInitialData> {
  const apiBaseUrl = process.env.API_BASE_URL;
  if (!apiBaseUrl) return {};
  const parameters = catalogParameters(filters);
  const requests: [Promise<Response>, Promise<Response> | undefined] = [
    fetch(`${apiBaseUrl}/api/v1/public/works?${parameters}`, {
      next: { revalidate: 60 },
    }),
    filters.page === 1 && !hasFilters(filters)
      ? fetch(`${apiBaseUrl}/api/v1/public/works/featured?limit=3`, {
          next: { revalidate: 30 },
        })
      : undefined,
  ];
  try {
    const [worksResponse, featuredResponse] = await Promise.all([
      requests[0],
      requests[1],
    ]);
    const works = worksResponse.ok
      ? ((await worksResponse.json()) as PublicCatalogPage)
      : undefined;
    const featured = featuredResponse?.ok
      ? ((await featuredResponse.json()) as SuccessEnvelope<PublicCatalogWork[]>)
      : undefined;
    return {
      works: works?.success && Array.isArray(works.data) ? works : undefined,
      featured:
        featured?.success && Array.isArray(featured.data)
          ? featured.data
          : undefined,
    };
  } catch {
    return {};
  }
}

function catalogParameters(filters: PublicCatalogFilters): string {
  const parameters = new URLSearchParams({
    page: String(filters.page ?? 1),
    pageSize: String(filters.pageSize ?? 12),
    sort: filters.sort ?? "newest",
  });
  for (const [name, value] of Object.entries({
    query: filters.query,
    category: filters.category,
    tag: filters.tag,
  })) {
    if (value) parameters.set(name, value);
  }
  if (filters.publishedFrom) {
    parameters.set("publishedFrom", `${filters.publishedFrom}T00:00:00Z`);
  }
  if (filters.publishedTo) {
    parameters.set("publishedTo", `${filters.publishedTo}T23:59:59Z`);
  }
  return parameters.toString();
}

function hasFilters(filters: PublicCatalogFilters): boolean {
  return Boolean(
    filters.query ||
      filters.category ||
      filters.tag ||
      filters.publishedFrom ||
      filters.publishedTo ||
      (filters.sort && filters.sort !== "newest"),
  );
}
