import type { SearchParameters } from "@/lib/api/types";

export function searchHref(parameters: SearchParameters): string {
  const query = new URLSearchParams();
  if (parameters.q) query.set("q", parameters.q);
  if (parameters.category) query.set("category", parameters.category);
  if (parameters.tags.length) query.set("tags", parameters.tags.join(","));
  if (parameters.tagsMode !== "any") query.set("tagsMode", parameters.tagsMode);
  if (parameters.organization)
    query.set("organization", parameters.organization);
  if (parameters.publishedFrom)
    query.set("publishedFrom", parameters.publishedFrom);
  if (parameters.publishedTo) query.set("publishedTo", parameters.publishedTo);
  if (parameters.hasBlockchainProof !== undefined) {
    query.set("hasBlockchainProof", String(parameters.hasBlockchainProof));
  }
  if (parameters.certificateStatus) {
    query.set("certificateStatus", parameters.certificateStatus);
  }
  query.set("sort", parameters.sort);
  if (parameters.cursor) query.set("cursor", parameters.cursor);
  return `/search?${query.toString()}`;
}
