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
  try {
    const raw = sessionStorage.getItem(key(owner));
    if (!raw || raw.length > 131072) return null;
    const parsed = backupSchema.safeParse(JSON.parse(raw));
    if (
      !parsed.success ||
      parsed.data.owner !== owner ||
      Date.now() - parsed.data.savedAt > 86_400_000
    )
      return null;
    return parsed.data;
  } catch {
    return null;
  }
}
export function writePreparationBackup(
  owner: string,
  revision: number,
  payload: DossierPreparationPayload,
) {
  try {
    sessionStorage.setItem(
      key(owner),
      JSON.stringify({ owner, revision, payload, savedAt: Date.now() }),
    );
    return true;
  } catch {
    return false;
  }
}
export function clearPreparationBackup(owner: string) {
  try {
    sessionStorage.removeItem(key(owner));
  } catch {
    /* Server state remains authoritative. */
  }
}
