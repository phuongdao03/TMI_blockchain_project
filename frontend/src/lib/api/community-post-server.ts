import "server-only";

import { cache } from "react";

import type { CommunityPostDetail, SuccessEnvelope } from "@/lib/api/types";
import { resolveServerApiBaseUrl } from "@/lib/api/server-base-url";

export const loadCommunityPost = cache(async (slug: string): Promise<CommunityPostDetail | null> => {
  try {
    const response = await fetch(
      `${resolveServerApiBaseUrl()}/api/v1/community/posts/${encodeURIComponent(slug)}`,
      { cache: "no-store" },
    );
    if (!response.ok) return null;
    const payload = (await response.json()) as SuccessEnvelope<CommunityPostDetail>;
    return payload.success ? payload.data : null;
  } catch {
    return null;
  }
});
