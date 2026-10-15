"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, LoaderCircle, RotateCcw } from "lucide-react";
import Link from "next/link";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityFeedHref } from "@/components/community/community-feed-url";
import { communityApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type { CommunityPostFilters, CommunityPostSort } from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityFeed({
  page,
  category,
  tag,
  q,
  sort = "recent",
  relatedWorkId,
}: {
  page: number;
  category?: string;
  tag?: string;
  q?: string;
  sort?: CommunityPostSort;
  relatedWorkId?: string;
}) {
  const user = useAuthUser();
  const viewerKey = user?.id ?? "anonymous";
  const categories = useQuery({
    queryKey: ["community", "categories"],
    queryFn: ({ signal }) => communityApi.categories(signal),
    staleTime: 5 * 60_000,
  });
  const posts = useQuery({
    queryKey: ["community", "posts", { page, category, tag, q, sort, relatedWorkId, viewerKey }],
    queryFn: ({ signal }) =>
      communityApi.posts({ page, category, tag, q, sort, relatedWorkId }, signal),
    staleTime: 30_000,
    enabled: !(sort === "following" && !user),
  });
  const needsFollowingLogin = sort === "following" && !user;
  const total = posts.data?.meta.total ?? 0;
  const totalPages = Math.max(
    1,
    Math.ceil(total / (posts.data?.meta.pageSize || PAGE_SIZE)),
  );

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16">
        <header className="flex flex-col gap-5 border-b border-[var(--theme-border)] pb-7 sm:flex-row sm:items-end sm:justify-between sm:pb-9">
          <div className="max-w-3xl">
            <p className="text-xs font-bold tracking-[0.2em] text-[var(--theme-accent)] uppercase">
              Tinh Hoa Việt · Kết nối và sẻ chia
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-[-0.035em] text-[var(--theme-text)] sm:text-5xl">
              Cộng đồng
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base sm:leading-7">
              Chia sẻ câu chuyện, ý tưởng và trải nghiệm làm nên những giá trị
              Việt.
            </p>
          </div>
          <Link
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-5 text-sm font-bold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href={user ? "/community/new" : `/login?next=${encodeURIComponent("/community/new")}`}
          >
            {user ? "Viết bài mới" : "Đăng nhập để viết bài"}
          </Link>
        </header>

        {!user ? (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm" role="status">
            <p className="text-[var(--theme-muted)]">Bạn đang ở chế độ chỉ đọc. Đăng nhập để đăng bài, bình luận và tương tác.</p>
            <Link className="font-bold text-[var(--theme-accent)] underline underline-offset-4" href={`/login?next=${encodeURIComponent("/community")}`}>Đăng nhập</Link>
          </div>
        ) : null}

        <section
          aria-labelledby="community-category-heading"
          className="border-b border-[var(--theme-border)] py-5 sm:py-6"
        >
          <h2
            className="mb-3 text-sm font-bold text-[var(--theme-text)]"
            id="community-category-heading"
          >
            Khám phá theo chuyên mục
          </h2>
          {categories.isPending ? (
            <p aria-busy="true" className="text-sm text-[var(--theme-muted)]" role="status">
              Đang tải chuyên mục…
            </p>
          ) : null}
          {categories.isError ? (
            <div className="flex flex-wrap items-center gap-3" role="alert">
              <p className="text-sm text-[var(--theme-muted)]">
                Chưa tải được danh sách chuyên mục.
              </p>
              <button
                className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-3 text-sm font-semibold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                onClick={() => void categories.refetch()}
                type="button"
              >
                <RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại
              </button>
            </div>
          ) : null}
          {categories.data ? (
            <nav
              aria-label="Lọc bài viết theo chuyên mục"
              className="flex gap-2 overflow-x-auto pb-1"
            >
              <Link
                aria-current={!category ? "page" : undefined}
                className={categoryClass(!category)}
                href={communityFeedHref({ category: undefined, tag, q, sort, relatedWorkId }, 1)}
              >
                Tất cả
              </Link>
              {categories.data.map((item) => (
                <Link
                  aria-current={category === item.slug ? "page" : undefined}
                  className={categoryClass(category === item.slug)}
                  href={communityFeedHref({ category: item.slug, tag, q, sort, relatedWorkId }, 1)}
                  key={item.id}
                >
                  {item.name}
                </Link>
              ))}
            </nav>
          ) : null}
        </section>

        <section aria-label="Tìm kiếm và sắp xếp bài viết" className="border-b border-[var(--theme-border)] py-5 sm:py-6">
          <form action="/community" aria-label="Tìm kiếm bài viết" className="flex flex-col gap-2 sm:flex-row" role="search">
            <label className="sr-only" htmlFor="community-feed-search">Tìm kiếm bài viết</label>
            <input
              className="min-h-11 min-w-0 flex-1 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm text-[var(--theme-text)] outline-none focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20"
              defaultValue={q ?? ""}
              id="community-feed-search"
              maxLength={120}
              name="q"
              placeholder="Tìm trong tiêu đề và nội dung"
              type="search"
            />
            {category ? <input name="category" type="hidden" value={category} /> : null}
            {tag ? <input name="tag" type="hidden" value={tag} /> : null}
            {relatedWorkId ? <input name="relatedWorkId" type="hidden" value={relatedWorkId} /> : null}
            {sort !== "recent" ? <input name="sort" type="hidden" value={sort} /> : null}
            <button className="min-h-11 rounded-lg bg-[var(--theme-accent)] px-5 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]" type="submit">
              Tìm bài viết
            </button>
          </form>
          <nav aria-label="Sắp xếp bài viết" className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {sortOptions.map((option) => {
              const filters: CommunityPostFilters = { category, tag, q, sort: option.value, relatedWorkId };
              const href = communityFeedHref(filters, 1);
              const selected = sort === option.value;
              const className = categoryClass(selected);
              const target = option.value === "following" && !user
                ? `/login?next=${encodeURIComponent(href)}`
                : href;
              return (
                <Link
                  aria-current={selected ? "page" : undefined}
                  className={className}
                  href={target}
                  key={option.value}
                >
                  {option.label}
                </Link>
              );
            })}
          </nav>
        </section>

        <section
          aria-label="Bài viết cộng đồng"
          aria-busy={!needsFollowingLogin && posts.isPending}
          className="min-w-0"
        >
          {needsFollowingLogin ? (
            <div className="my-8 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5" role="status">
              <p className="font-bold text-[var(--theme-text)]">Đăng nhập để xem bài viết từ người bạn theo dõi.</p>
              <Link className="mt-3 inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]" href={`/login?next=${encodeURIComponent(communityFeedHref({ category, tag, q, sort, relatedWorkId }, page))}`}>
                Đăng nhập
              </Link>
            </div>
          ) : null}
          {!needsFollowingLogin && posts.isPending ? <FeedSkeleton /> : null}
          {!needsFollowingLogin && posts.isError ? (
            <div className="my-8 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 sm:p-8">
              <p className="font-bold text-[var(--theme-text)]">
                Chưa thể tải bài viết cộng đồng.
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                Kiểm tra kết nối rồi thử lại.
              </p>
              <button
                className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                onClick={() => void posts.refetch()}
                type="button"
              >
                <RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại
              </button>
            </div>
          ) : null}
          {!needsFollowingLogin && posts.data?.data.length === 0 ? (
            <div className="my-8 rounded-2xl border border-dashed border-[var(--theme-border)] px-5 py-12 text-center sm:py-16">
              <h2 className="text-xl font-bold text-[var(--theme-text)]">
                {category
                  ? "Chưa có bài viết trong chuyên mục này."
                  : "Chưa có bài viết nào."}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                Hãy bắt đầu bằng một câu chuyện hoặc ý tưởng của bạn.
              </p>
              <Link
                className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                href="/community/new"
              >
                Viết bài đầu tiên
              </Link>
            </div>
          ) : null}
          {!needsFollowingLogin && posts.data?.data.length ? (
            <>
              <div className="divide-y divide-[var(--theme-border)]">
                {posts.data.data.map((post) => (
                  <CommunityPostCard
                    filters={{ category, tag, q, sort, relatedWorkId }}
                    key={post.id}
                    post={post}
                  />
                ))}
              </div>
              {totalPages > 1 ? (
                <nav
                  aria-label="Phân trang bài viết cộng đồng"
                  className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
                >
                  {page > 1 ? (
                    <Link
                      className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                      href={communityFeedHref({ category, tag, q, sort, relatedWorkId }, page - 1)}
                    >
                      <ArrowLeft aria-hidden="true" className="size-4" /> Trang
                      trước
                    </Link>
                  ) : (
                    <span />
                  )}
                  <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">
                    Trang {page} / {totalPages}
                  </p>
                  {page < totalPages ? (
                    <Link
                      className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                      href={communityFeedHref({ category, tag, q, sort, relatedWorkId }, page + 1)}
                    >
                      Trang sau <ArrowRight aria-hidden="true" className="size-4" />
                    </Link>
                  ) : (
                    <span />
                  )}
                </nav>
              ) : null}
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function categoryClass(active: boolean): string {
  return [
    "inline-flex min-h-10 shrink-0 items-center rounded-full border px-4 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]",
    active
      ? "border-[var(--theme-accent)] bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]"
      : "border-[var(--theme-border)] text-[var(--theme-muted)] hover:border-[var(--theme-accent)] hover:text-[var(--theme-text)]",
  ].join(" ");
}

const sortOptions: { value: CommunityPostSort; label: string }[] = [
  { value: "recent", label: "Mới nhất" },
  { value: "popular", label: "Nổi bật" },
  { value: "discussed", label: "Thảo luận nhiều" },
  { value: "following", label: "Đang theo dõi" },
];

function FeedSkeleton() {
  return (
    <div aria-label="Đang tải bài viết cộng đồng" className="py-4" role="status">
      {Array.from({ length: 3 }, (_, index) => (
        <div
          aria-hidden="true"
          className="animate-pulse border-b border-[var(--theme-border)] py-7"
          key={index}
        >
          <div className="h-3 w-40 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-4 h-6 w-3/4 rounded bg-[var(--theme-elevated)]" />
          <div className="mt-3 h-4 w-full max-w-2xl rounded bg-[var(--theme-elevated)]" />
        </div>
      ))}
      <span className="sr-only">
        <LoaderCircle aria-hidden="true" className="animate-spin" /> Đang tải
      </span>
    </div>
  );
}
