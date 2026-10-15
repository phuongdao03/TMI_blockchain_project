"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityApi, communityMemberApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  CommunityPageResponse,
  CommunityPostSummary,
} from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunitySavedPosts({ page }: { page: number }) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState("");
  const bookmarksKey = ["community", "bookmarks", page, viewerKey] as const;
  const bookmarks = useQuery({
    queryKey: bookmarksKey,
    queryFn: ({ signal }) => communityMemberApi.bookmarks(page, signal),
    staleTime: 30_000,
  });
  const removeBookmark = useMutation({
    mutationFn: (postId: string) => communityApi.unbookmarkPost(postId),
    onSuccess: (_result, postId) => {
      setNotice("Bài viết đã được bỏ lưu.");
      queryClient.setQueryData<CommunityPageResponse<CommunityPostSummary[]>>(
        bookmarksKey,
        (current) =>
          current
            ? {
                ...current,
                data: current.data.filter((post) => post.id !== postId),
                meta: {
                  ...current.meta,
                  total: Math.max(0, current.meta.total - 1),
                },
              }
            : current,
      );
      queryClient.setQueriesData<CommunityPageResponse<CommunityPostSummary[]>>(
        { queryKey: ["community", "posts"] },
        (current) =>
          current
            ? {
                ...current,
                data: current.data.map((post) =>
                  post.id === postId
                    ? { ...post, viewerHasBookmarked: false }
                    : post,
                ),
              }
            : current,
      );
    },
  });
  const posts = bookmarks.data?.data ?? [];
  const total = bookmarks.data?.meta.total ?? 0;
  const totalPages = Math.max(
    1,
    Math.ceil(total / (bookmarks.data?.meta.pageSize || PAGE_SIZE)),
  );

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <Link
          className="inline-flex min-h-10 items-center text-sm font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)]"
          href="/community"
        >
          ← Về cộng đồng
        </Link>
        <header className="mt-5 flex flex-wrap items-end justify-between gap-3 border-b border-[var(--theme-border)] pb-5">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
              Thư viện cá nhân
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl">
              Bài đã lưu
            </h1>
          </div>
          {bookmarks.data ? (
            <p className="text-sm text-[var(--theme-muted)]">
              {total} bài viết
            </p>
          ) : null}
        </header>

        {notice ? (
          <p
            aria-live="polite"
            className="mt-4 text-sm font-semibold text-[var(--theme-accent)]"
            role="status"
          >
            {notice}
          </p>
        ) : null}
        {removeBookmark.isError ? (
          <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
            Chưa thể bỏ lưu bài viết. Vui lòng thử lại.
          </p>
        ) : null}
        {bookmarks.isPending ? <SavedPostsSkeleton /> : null}
        {bookmarks.isError ? (
          <div
            className="mt-6 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5"
            role="alert"
          >
            <h2 className="font-bold text-[var(--theme-text)]">
              Chưa thể tải bài đã lưu.
            </h2>
            <button
              className={actionClass}
              onClick={() => void bookmarks.refetch()}
              type="button"
            >
              Thử tải lại
            </button>
          </div>
        ) : null}
        {bookmarks.data && posts.length === 0 ? (
          <div className="mt-7 rounded-2xl border border-dashed border-[var(--theme-border)] px-5 py-12 text-center">
            <h2 className="text-xl font-bold text-[var(--theme-text)]">
              Bạn chưa lưu bài viết nào.
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
              Lưu lại câu chuyện bạn muốn đọc tiếp sau.
            </p>
            <Link
              className="mt-5 inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href="/community"
            >
              Khám phá bài viết
            </Link>
          </div>
        ) : null}
        {posts.length > 0 ? (
          <div className="mt-4 divide-y divide-[var(--theme-border)]">
            {posts.map((post) => (
              <article className="relative" key={post.id}>
                <CommunityPostCard post={post} />
                <button
                  aria-label={`Bỏ lưu bài viết: ${post.title}`}
                  className="mb-5 inline-flex min-h-10 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:opacity-50"
                  disabled={removeBookmark.isPending}
                  onClick={() => removeBookmark.mutate(post.id)}
                  type="button"
                >
                  <BookmarkX aria-hidden="true" className="size-4" /> Bỏ lưu bài
                  viết
                </button>
              </article>
            ))}
          </div>
        ) : null}
        {totalPages > 1 ? (
          <nav
            aria-label="Phân trang bài đã lưu"
            className="flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
          >
            {page > 1 ? (
              <Link
                className={paginationClass}
                href={`/community/saved?page=${page - 1}`}
              >
                Trang trước
              </Link>
            ) : (
              <span aria-disabled="true" className={paginationClass}>
                Trang trước
              </span>
            )}
            <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
              Trang {page} / {totalPages}
            </p>
            {page < totalPages ? (
              <Link
                className={paginationClass}
                href={`/community/saved?page=${page + 1}`}
              >
                Trang sau
              </Link>
            ) : (
              <span aria-disabled="true" className={paginationClass}>
                Trang sau
              </span>
            )}
          </nav>
        ) : null}
      </div>
    </div>
  );
}

function SavedPostsSkeleton() {
  return (
    <div
      aria-label="Đang tải bài đã lưu"
      className="mt-5 space-y-4"
      role="status"
    >
      {Array.from({ length: 3 }, (_, index) => (
        <div
          aria-hidden="true"
          className="h-32 animate-pulse rounded-xl bg-[var(--theme-elevated)]"
          key={index}
        />
      ))}
    </div>
  );
}

const actionClass =
  "mt-4 inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
const paginationClass =
  "inline-flex min-h-10 items-center rounded-lg border border-[var(--theme-border)] px-3 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
