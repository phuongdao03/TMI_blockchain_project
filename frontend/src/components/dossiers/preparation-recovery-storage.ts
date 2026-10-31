import { z } from "zod";
import type { DossierPreparationPayload } from "@/lib/api/types";

export const EMPTY_PREPARATION: DossierPreparationPayload = {
  dossierTypeVersionId: null,
  step: 0,
  values: { title: "", summary: "", visibility: "PRIVATE" },
  formData: {},
};
const backupSchema = z.object({
  owner: z.string(),
  revision: z.number().int().nonnegative(),
  savedAt: z.number(),
  payload: z.object({
    dossierTypeVersionId: z.string().nullable(),
    step: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
    values: z.object({
      title: z.string().max(255),
      summary: z.string().max(10000),
      visibility: z.enum(["PRIVATE", "PUBLIC", "UNLISTED"]),
    }),
    formData: z.record(z.string(), z.json()),
  }),
});
const key = (owner: string) => `thv:dossier-preparation:${owner}`;
// Survives client-side back/forward when browser storage is unavailable.
// Owner matching and the existing logout cleanup also apply to this fallback.
let volatileBackup: {
  owner: string;
  revision: number;
  savedAt: number;
  payload: DossierPreparationPayload;
} | null = null;

export function serializePreparation(value: DossierPreparationPayload | null) {
  return JSON.stringify(value, (_name, item: unknown) =>
    item && typeof item === "object" && !Array.isArray(item)
      ? Object.fromEntries(
          Object.entries(item).sort(([a], [b]) => a.localeCompare(b)),
        )
      : item,
  );
}
export function readPreparationBackup(owner: string) {
  const memory =
    volatileBackup?.owner === owner &&
    Date.now() - volatileBackup.savedAt <= 86_400_000
      ? volatileBackup
      : null;
  try {
    const raw = sessionStorage.getItem(key(owner));
    if (!raw || raw.length > 131072) return memory;
    const parsed = backupSchema.safeParse(JSON.parse(raw));
    if (
      !parsed.success ||
      parsed.data.owner !== owner ||
      Date.now() - parsed.data.savedAt > 86_400_000
    )
      return memory;
    return memory && memory.savedAt >= parsed.data.savedAt
      ? memory
      : parsed.data;
  } catch {
    return memory;
  }
}
export function writePreparationBackup(
  owner: string,
  revision: number,
  payload: DossierPreparationPayload,
) {
  const backup = { owner, revision, payload, savedAt: Date.now() };
  volatileBackup = structuredClone(backup);
  try {
    sessionStorage.setItem(key(owner), JSON.stringify(backup));
    return true;
  } catch {
    return false;
  }
}
export function clearPreparationBackup(owner: string) {
  if (volatileBackup?.owner === owner) volatileBackup = null;
  try {
    sessionStorage.removeItem(key(owner));
  } catch {
    /* Server state remains authoritative. */
  }
}
