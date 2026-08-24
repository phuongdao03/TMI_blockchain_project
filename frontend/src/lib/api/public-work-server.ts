import "server-only";

import { cache } from "react";

import type { PublicWorkDetail, SuccessEnvelope } from "@/lib/api/types";
import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";

export type PublicWorkServerResult =
  | { kind: "detail"; detail: PublicWorkDetail }
  | { kind: "redirect"; slug: string }
  | { kind: "not_found" }
  | { kind: "unavailable" };

export const loadPublicWork = cache(
  async (slug: string): Promise<PublicWorkServerResult> => {
    const apiBaseUrl = resolveServerApiBaseUrl();
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/v1/public/works/${encodeURIComponent(slug)}`,
        { cache: "no-store", redirect: "manual" },
      );
      if (response.status === 308 || response.status === 301) {
        const location = response.headers.get("location");
        const canonical = location?.split("/").filter(Boolean).at(-1);
        return canonical
          ? { kind: "redirect", slug: decodeURIComponent(canonical) }
          : { kind: "not_found" };
      }
      if (response.status === 404) return { kind: "not_found" };
      if (!response.ok) return { kind: "unavailable" };
      const payload =
        (await response.json()) as SuccessEnvelope<PublicWorkDetail>;
      return payload.success
        ? { kind: "detail", detail: payload.data }
        : { kind: "unavailable" };
    } catch {
      return { kind: "unavailable" };
    }
  },
);
