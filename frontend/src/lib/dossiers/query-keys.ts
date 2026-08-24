import type { DossierListFilters } from "@/lib/api/types";

export const dossierKeys = {
  all: ["dossiers"] as const,
  lists: () => [...dossierKeys.all, "list"] as const,
  types: () => [...dossierKeys.all, "types"] as const,
  list: (filters: DossierListFilters) =>
    [...dossierKeys.lists(), filters] as const,
  details: () => [...dossierKeys.all, "detail"] as const,
  detail: (dossierId: string) => [...dossierKeys.details(), dossierId] as const,
  versions: (dossierId: string) =>
    [...dossierKeys.detail(dossierId), "versions"] as const,
  timeline: (dossierId: string) =>
    [...dossierKeys.detail(dossierId), "timeline"] as const,
};
