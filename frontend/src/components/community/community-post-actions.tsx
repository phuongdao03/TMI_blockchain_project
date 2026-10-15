"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Heart } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CommunityReportAction } from "@/components/community/community-report-action";
import { communityApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  CommunityPageResponse,
  CommunityPostDetail,
  CommunityPostSummary,
} from "@/lib/api/types";

export interface CommunityInteractionPost {
  id: string;
  slug: string;
  likeCount: number;
  commentCount: number;
  viewerHasLiked: boolean;
  viewerHasBookmarked: boolean;
}

export function CommunityPostActions({ post }: { post: CommunityInteractionPost }) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const queryClient = useQueryClient();
  const [isLiked, setIsLiked] = useState(post.viewerHasLiked);
  const [isBookmarked, setIsBookmarked] = useState(post.viewerHasBookmarked);
  const [likeCount, setLikeCount] = useState(post.likeCount);
  const like = useMutation({
    mutationFn: () =>
      isLiked ? communityApi.unlikePost(post.id) : communityApi.likePost(post.id),
    onSuccess: (result) => {
      setIsLiked(result.isLiked);
      setLikeCount(result.likeCount);
      updatePostCaches(queryClient, post, viewerKey, {
        likeCount: result.likeCount,
        viewerHasLiked: result.isLiked,
      });
    },
  });
  const bookmark = useMutation({
    mutationFn: () =>
      isBookmarked
        ? communityApi.unbookmarkPost(post.id)
        : communityApi.bookmarkPost(post.id),
    onSuccess: (result) => {
      setIsBookmarked(result.isBookmarked);
      updatePostCaches(queryClient, post, viewerKey, {
        viewerHasBookmarked: result.isBookmarked,
      });
      if (!result.isBookmarked) {
        void queryClient.invalidateQueries({ queryKey: ["community", "bookmarks"] });
      }
    },
  });

  if (!user) {
    return (
      <div className="mt-7 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
        <p className="text-sm text-[var(--theme-muted)]">
          Đăng nhập để thích bài viết, lưu lại và tham gia thảo luận.
        </p>
        <Link
          className="mt-3 inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href={`/login?next=${encodeURIComponent(`/community/posts/${encodeURIComponent(post.slug)}`)}`}
        >
          Đăng nhập để tham gia
        </Link>
        <div className="mt-2">
          <CommunityReportAction targetId={post.id} targetLabel={`Bài viết: ${post.slug}`} targetType="POST" />
        </div>
      </div>
    );
  }

  return (
    <div className="mt-7 flex flex-wrap items-center gap-3 border-y border-[var(--theme-border)] py-4">
      <button
        aria-pressed={isLiked}
        className={actionClass(isLiked)}
        disabled={like.isPending || bookmark.isPending}
        onClick={() => like.mutate()}
        type="button"
      >
        <Heart aria-hidden="true" className={isLiked ? "size-4 fill-current" : "size-4"} />
        {isLiked ? "Bỏ thích bài viết" : "Thích bài viết"}
      </button>
      <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
        {likeCount} lượt thích
      </p>
      <button
        aria-pressed={isBookmarked}
        className={actionClass(isBookmarked)}
        disabled={like.isPending || bookmark.isPending}
        onClick={() => bookmark.mutate()}
        type="button"
      >
        <Bookmark aria-hidden="true" className={isBookmarked ? "size-4 fill-current" : "size-4"} />
        {isBookmarked ? "Đã lưu bài viết" : "Lưu bài viết"}
      </button>
      <Link
        className="inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-semibold text-[var(--theme-accent)] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
        href="/community/saved"
      >
        Bài đã lưu
      </Link>
      <CommunityReportAction targetId={post.id} targetLabel={`Bài viết: ${post.slug}`} targetType="POST" />
      {like.isError || bookmark.isError ? (
        <p className="basis-full text-sm font-semibold text-red-700" role="alert">
          Chưa thể cập nhật. Vui lòng kiểm tra kết nối hoặc đăng nhập rồi thử lại.
        </p>
      ) : null}
    </div>
  );
}

function actionClass(active: boolean): string {
  return [
    "inline-flex min-h-10 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-60",
    active
      ? "border-[var(--theme-accent)] bg-[var(--theme-accent)]/10 text-[var(--theme-accent)]"
      : "border-[var(--theme-border)] text-[var(--theme-text)] hover:border-[var(--theme-accent)]",
  ].join(" ");
}

function updatePostCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  post: CommunityInteractionPost,
  viewerKey: string,
  change: Partial<Pick<CommunityPostSummary, "likeCount" | "viewerHasLiked" | "viewerHasBookmarked">>,
) {
  queryClient.setQueryData<CommunityPostDetail>(
    ["community", "post", post.slug, viewerKey],
    (current) => (current ? { ...current, ...change } : current),
  );
  queryClient.setQueriesData<CommunityPageResponse<CommunityPostSummary[]>>(
    { queryKey: ["community", "posts"] },
    (current) =>
      current
        ? {
            ...current,
            data: current.data.map((item) =>
              item.id === post.id ? { ...item, ...change } : item,
            ),
          }
        : current,
  );
}
