import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CommunityPostEditor } from "@/components/community/community-post-editor";
import { getServerAuthState } from "@/lib/auth/server-session";
import { loadPublicWork } from "@/lib/api/public-work-server";

export const metadata: Metadata = {
  title: "Viết bài cộng đồng",
};

export default async function CommunityNewPage({
  searchParams,
}: {
  searchParams?: Promise<{
    postId?: string | string[];
    relatedWorkId?: string | string[];
    relatedWorkSlug?: string | string[];
  }>;
}) {
  const input = (await searchParams) ?? {};
  const postId = one(input.postId)?.trim().slice(0, 100) || undefined;
  const relatedWorkId = one(input.relatedWorkId)?.trim().slice(0, 100) || undefined;
  const relatedWorkSlug = one(input.relatedWorkSlug)?.trim().slice(0, 100) || undefined;
  const params = new URLSearchParams();
  if (postId) params.set("postId", postId);
  if (relatedWorkId && relatedWorkSlug) {
    params.set("relatedWorkId", relatedWorkId);
    params.set("relatedWorkSlug", relatedWorkSlug);
  }
  const next = `/community/new${params.size ? `?${params.toString()}` : ""}`;
  const authState = await getServerAuthState();
  if (!authState.user && !authState.hasRefreshCookie) {
    redirect(`/login?next=${encodeURIComponent(next)}`);
  }

  let relatedWork = null;
  if (relatedWorkId && relatedWorkSlug && /^[\p{L}\p{N}-]+$/u.test(relatedWorkSlug)) {
    const result = await loadPublicWork(relatedWorkSlug);
    if (result.kind === "detail" && result.detail.id === relatedWorkId) {
      relatedWork = {
        id: result.detail.id,
        title: result.detail.title,
        slug: result.detail.canonicalSlug,
      };
    }
  }
  return <CommunityPostEditor postId={postId} relatedWork={relatedWork} />;
}

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
