"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import { CommunityPostEngagement } from "@/components/community/community-post-engagement";
import { CommunityPostImages } from "@/components/community/community-post-images";
import { CommunityMarkdown } from "@/components/community/community-markdown";
import { CommunityRelatedWorkLink } from "@/components/community/community-related-work-link";
import { CommunityUserIdentity } from "@/components/community/community-user-identity";
import { communityApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";

export function CommunityPostDetail({ slug }: { slug: string }) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const recordedViews = useRef(new Set<string>());
  const post = useQuery({
    queryKey: ["community", "post", slug, viewerKey],
    queryFn: ({ signal }) => communityApi.post(slug, signal),
    staleTime: 60_000,
  });
  useEffect(() => {
    const postId = post.data?.id;
    if (!postId || recordedViews.current.has(postId)) return;
    recordedViews.current.add(postId);
    void communityApi.recordPostView(postId).catch(() => undefined);
  }, [post.data?.id]);

  if (post.isPending) {
    return (
      <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
        <div
          aria-label="Đang tải bài viết"
          className="mx-auto max-w-4xl animate-pulse px-4 py-12 sm:px-6 lg:px-8"
          role="status"
        >
          <div className="h-4 w-32 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-7 h-10 w-4/5 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-5 h-5 w-48 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-12 space-y-3">
            <div className="h-4 rounded bg-[var(--theme-elevated)]" />
            <div className="h-4 w-11/12 rounded bg-[var(--theme-elevated)]" />
            <div className="h-4 w-4/5 rounded bg-[var(--theme-elevated)]" />
          </div>
        </div>
      </div>
    );
  }

  if (post.isError && isNotFound(post.error)) {
    return (
      <StatePanel
        heading="Không tìm thấy bài viết"
        message="Bài viết có thể đã bị gỡ hoặc chưa được công bố."
      />
    );
  }

  if (post.isError || !post.data) {
    return (
      <StatePanel
        action={
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            onClick={() => void post.refetch()}
            type="button"
          >
            <RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại
          </button>
        }
        heading="Chưa thể tải bài viết"
        message="Kiểm tra kết nối rồi thử lại."
        role="alert"
      />
    );
  }

  const article = post.data;
  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <article className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16">
        <Link
          className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--theme-accent)]"
          href="/community"
        >
          <ArrowLeft aria-hidden="true" className="size-4" /> Về cộng đồng
        </Link>
        <header className="mt-7 border-b border-[var(--theme-border)] pb-7 sm:mt-10 sm:pb-9">
          <p className="text-xs font-bold tracking-[0.18em] text-[var(--theme-accent)] uppercase">
            {article.category.name}
          </p>
          <h1 className="mt-3 text-3xl font-bold leading-tight tracking-[-0.035em] text-[var(--theme-text)] sm:text-5xl">
            {article.title}
          </h1>
          <div className="mt-5 flex flex-col items-start gap-3 text-sm text-[var(--theme-muted)] sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4">
            <CommunityUserIdentity size={40} user={article.author} />
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <time dateTime={article.publishedAt}>
                {formatPublishedDate(article.publishedAt)}
              </time>
              <span aria-label={`${article.viewCount} lượt xem`}>
                {article.viewCount} lượt xem
              </span>
            </div>
          </div>
        </header>
        <CommunityPostImages
          images={article.images ?? []}
          postSlug={article.slug}
          postTitle={article.title}
          priority
        />
        <CommunityRelatedWorkLink work={article.relatedWork} />
        <div className="mt-7 text-base leading-8 sm:mt-9 sm:text-lg sm:leading-9">
          <CommunityMarkdown content={article.content} />
        </div>
        <CommunityPostEngagement post={article} />
      </article>
    </div>
  );
}

function StatePanel({
  action,
  heading,
  message,
  role,
}: {
  action?: React.ReactNode;
  heading: string;
  message: string;
  role?: "alert";
}) {
  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)] px-4 py-16 sm:px-6 lg:px-8">
      <section
        className="mx-auto max-w-2xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-7 text-center sm:p-10"
        role={role}
      >
        <h1 className="text-2xl font-bold text-[var(--theme-text)]">
          {heading}
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">
          {message}
        </p>
        {action ? <div className="mt-5">{action}</div> : null}
        <Link
          className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href="/community"
        >
          Về cộng đồng
        </Link>
      </section>
    </div>
  );
}

function isNotFound(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    error.status === 404
  );
}

function formatPublishedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" }).format(date);
}
