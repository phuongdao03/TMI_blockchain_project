import type { CommunityPostFilters } from "@/lib/api/types";

export function communityFeedHref(
  filters: CommunityPostFilters,
  page: number,
): string {
  const parameters = new URLSearchParams();
  if (filters.category) parameters.set("category", filters.category);
  if (filters.tag) parameters.set("tag", filters.tag);
  if (filters.relatedWorkId)
    parameters.set("relatedWorkId", filters.relatedWorkId);
  if (filters.q?.trim()) parameters.set("q", filters.q.trim());
  if (filters.sort && filters.sort !== "recent")
    parameters.set("sort", filters.sort);
  parameters.set("page", String(page));
  return `/community?${parameters.toString()}`;
}
