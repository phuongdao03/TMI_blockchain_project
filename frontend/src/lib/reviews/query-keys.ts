import type { ReviewListFilters } from "@/lib/api/types";

export const reviewKeys = {
  all: ["review-assignments"] as const,
  lists: () => [...reviewKeys.all, "list"] as const,
  list: (filters: ReviewListFilters) =>
    [...reviewKeys.lists(), filters] as const,
  details: () => [...reviewKeys.all, "detail"] as const,
  detail: (assignmentId: string) =>
    [...reviewKeys.details(), assignmentId] as const,
};
