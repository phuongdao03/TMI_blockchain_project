import type { CouncilListFilters } from "@/lib/api/types";

export const councilKeys = {
  all: ["council"] as const,
  lists: () => [...councilKeys.all, "list"] as const,
  list: (filters: CouncilListFilters) =>
    [...councilKeys.lists(), filters] as const,
  details: () => [...councilKeys.all, "detail"] as const,
  detail: (sessionId: string) => [...councilKeys.details(), sessionId] as const,
};
