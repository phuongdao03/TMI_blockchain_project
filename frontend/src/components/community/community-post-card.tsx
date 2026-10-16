"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Heart, Share2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CommunityPostImages } from "@/components/community/community-post-images";
import { CommunityRelatedWorkLink } from "@/components/community/community-related-work-link";
import { CommunityUserIdentity } from "@/components/community/community-user-identity";
import { communityApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  CommunityPageResponse,
  CommunityPostSummary,
} from "@/lib/api/types";

export function CommunityPostCard(props: { post: CommunityPostSummary }) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const interactionKey = `${props.post.id}:${viewerKey}:${props.post.likeCount}:${props.post.viewerHasLiked}:${props.post.viewerHasBookmarked}`;
  return (
    <CommunityPostCardContent
      {...props}
      authenticated={Boolean(user)}
      key={interactionKey}
      viewerKey={viewerKey}
    />
  );
}

function CommunityPostCardContent({
  post,
  authenticated,
  viewerKey,
}: {
  post: CommunityPostSummary;
  authenticated: boolean;
  viewerKey: string;
}) {
  const queryClient = useQueryClient();
  const [liked, setLiked] = useState(post.viewerHasLiked);
  const [bookmarked, setBookmarked] = useState(post.viewerHasBookmarked);
  const [likeCount, setLikeCount] = useState(post.likeCount);
  const [shareMessage, setShareMessage] = useState("");
  const [shareFallback, setShareFallback] = useState(false);
  const like = useMutation({
    mutationFn: () =>
      liked ? communityApi.unlikePost(post.id) : communityApi.likePost(post.id),
    onSuccess: (result) => {
      setLiked(result.isLiked);
      setLikeCount(result.likeCount);
      updatePostCaches(queryClient, post, viewerKey, {
        likeCount: result.likeCount,
        viewerHasLiked: result.isLiked,
      });
    },
  });
  const bookmark = useMutation({
    mutationFn: () =>
      bookmarked
        ? communityApi.unbookmarkPost(post.id)
        : communityApi.bookmarkPost(post.id),
    onSuccess: (result) => {
      setBookmarked(result.isBookmarked);
      updatePostCaches(queryClient, post, viewerKey, {
        viewerHasBookmarked: result.isBookmarked,
      });
      if (!result.isBookmarked)
        void queryClient.invalidateQueries({
          queryKey: ["community", "bookmarks"],
        });
    },
  });

  async function sharePost() {
    const url = `${window.location.origin}/community/posts/${encodeURIComponent(post.slug)}`;
    setShareMessage("");
    if (navigator.share) {
      try {
        await navigator.share({ title: post.title, url });
      } catch {
        /* User cancelled the native share sheet. */
      }
      return;
    }
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(url);
        setShareMessage("Đã sao chép liên kết bài viết.");
      } catch {
        setShareFallback(true);
      }
      return;
    }
    setShareFallback(true);
  }

  const postHref = `/community/posts/${encodeURIComponent(post.slug)}`;
  return (
    <article className="border-b border-[var(--theme-border)] py-6 first:border-t sm:py-7">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs font-semibold text-[var(--theme-muted)]">
        <CommunityUserIdentity size={36} user={post.author} />
        <span aria-hidden="true">·</span>
        <span className="text-[var(--theme-accent)]">{post.category.name}</span>
        <time dateTime={post.publishedAt}>
          {formatPublishedDate(post.publishedAt)}
        </time>
      </div>
      <h2 className="mt-3 text-xl font-bold leading-snug tracking-tight text-[var(--theme-text)] sm:text-2xl">
        <Link
          className="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)] hover:text-[var(--theme-accent)]"
          href={postHref}
        >
          {post.title}
        </Link>
      </h2>
      {post.excerpt ? (
        <p className="mt-2 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-[var(--theme-muted)] sm:text-base sm:leading-7">
          {post.excerpt}
        </p>
      ) : null}
      <CommunityPostImages
        images={post.images ?? []}
        postSlug={post.slug}
        postTitle={post.title}
      />
      <CommunityRelatedWorkLink work={post.relatedWork} />
      <div
        aria-label="Tương tác bài viết"
        className="mt-4 flex flex-wrap items-center gap-2 border-t border-[var(--theme-border)] pt-3"
      >
        {authenticated ? (
          <>
            <button
              aria-pressed={liked}
              className={quickActionClass(liked)}
              disabled={like.isPending || bookmark.isPending}
              onClick={() => like.mutate()}
              type="button"
            >
              <Heart
                aria-hidden="true"
                className={liked ? "size-4 fill-current" : "size-4"}
              />
              {liked ? "Bỏ thích" : "Thích"} bài viết ({likeCount})
            </button>
            <button
              aria-pressed={bookmarked}
              className={quickActionClass(bookmarked)}
              disabled={like.isPending || bookmark.isPending}
              onClick={() => bookmark.mutate()}
              type="button"
            >
              <Bookmark
                aria-hidden="true"
                className={bookmarked ? "size-4 fill-current" : "size-4"}
              />
              {bookmarked ? "Đã lưu" : "Lưu bài viết"}
            </button>
          </>
        ) : (
          <Link
            className={quickActionClass(false)}
            href={`/login?next=${encodeURIComponent(postHref)}`}
          >
            Đăng nhập để tương tác
          </Link>
        )}
        <Link
          className={quickActionClass(false)}
          href={`${postHref}#community-comments-title`}
        >
          {post.commentCount} bình luận
        </Link>
        <span className="px-2 text-xs text-[var(--theme-muted)]">
          {post.viewCount} lượt xem
        </span>
        <button
          aria-label="Chia sẻ bài viết"
          className={quickActionClass(false)}
          onClick={() => void sharePost()}
          type="button"
        >
          <Share2 aria-hidden="true" className="size-4" />
          Chia sẻ
        </button>
        {shareMessage ? (
          <span className="text-xs text-[var(--theme-muted)]" role="status">
            {shareMessage}
          </span>
        ) : null}
        {shareFallback ? (
          <label className="basis-full text-xs text-[var(--theme-muted)]">
            Sao chép liên kết bài viết
            <input
              aria-label="Liên kết bài viết"
              className="mt-1 min-h-10 w-full rounded border border-[var(--theme-border)] bg-[var(--theme-surface)] px-2 text-[var(--theme-text)]"
              onFocus={(event) => event.currentTarget.select()}
              readOnly
              value={
                typeof window === "undefined"
                  ? postHref
                  : `${window.location.origin}${postHref}`
              }
            />
          </label>
        ) : null}
        {like.isError || bookmark.isError ? (
          <span
            className="basis-full text-sm font-semibold text-red-700"
            role="alert"
          >
            Chưa thể cập nhật tương tác. Vui lòng thử lại.
          </span>
        ) : null}
      </div>
      <Link
        className="mt-3 inline-flex min-h-10 items-center text-sm font-bold text-[var(--theme-accent)] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)]"
        href={postHref}
      >
        Đọc bài viết{" "}
        <span aria-hidden="true" className="ml-1">
          →
        </span>
      </Link>
    </article>
  );
}

function updatePostCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  post: CommunityPostSummary,
  viewerKey: string,
  change: Partial<
    Pick<
      CommunityPostSummary,
      "likeCount" | "viewerHasLiked" | "viewerHasBookmarked"
    >
  >,
) {
  queryClient.setQueryData(
    ["community", "post", post.slug, viewerKey],
    (current: unknown) =>
      current && typeof current === "object"
        ? { ...current, ...change }
        : current,
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

function quickActionClass(active: boolean): string {
  return `inline-flex min-h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-60 ${active ? "border-[var(--theme-accent)] bg-[var(--theme-accent)]/10 text-[var(--theme-accent)]" : "border-[var(--theme-border)] text-[var(--theme-muted)] hover:border-[var(--theme-accent)] hover:text-[var(--theme-text)]"}`;
}

function formatPublishedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}
