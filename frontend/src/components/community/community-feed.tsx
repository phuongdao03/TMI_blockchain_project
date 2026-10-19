"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  LoaderCircle,
  RotateCcw,
  Search,
} from "lucide-react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityFeedHref } from "@/components/community/community-feed-url";
import { communityApi } from "@/lib/api/client";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";
import type { CommunityPostSort } from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityFeed({
  page,
  category,
  q,
  sort = "recent",
  relatedWorkId,
}: {
  page: number;
  category?: string;
  q?: string;
  sort?: CommunityPostSort;
  relatedWorkId?: string;
}) {
  const router = useRouter();
  const user = useAuthUser();
  const authStatus = useAuthStatus();
  const viewerKey = user?.id ?? "anonymous";
  const categories = useQuery({
    queryKey: ["community", "categories"],
    queryFn: ({ signal }) => communityApi.categories(signal),
    staleTime: 5 * 60_000,
  });
  const posts = useQuery({
    queryKey: [
      "community",
      "posts",
      { page, category, q, sort, relatedWorkId, viewerKey },
    ],
    queryFn: ({ signal }) =>
      communityApi.posts({ page, category, q, sort, relatedWorkId }, signal),
    staleTime: 30_000,
    enabled: !(sort === "following" && authStatus !== "authenticated"),
  });
  const needsFollowingLogin =
    sort === "following" && authStatus === "unauthenticated";
  const needsAuthCheck =
    sort === "following" &&
    (authStatus === "loading" || authStatus === "error");
  const total = posts.data?.meta.total ?? 0;
  const totalPages = Math.max(
    1,
    Math.ceil(total / (posts.data?.meta.pageSize || PAGE_SIZE)),
  );

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>) {
    const data = new FormData(event.currentTarget);
    if (data.get("sort") === "following" && authStatus === "unauthenticated") {
      event.preventDefault();
      const href = communityFeedHref(
        {
          category: String(data.get("category") || "") || undefined,
          q: String(data.get("q") || "") || undefined,
          sort: "following",
          relatedWorkId,
        },
        1,
      );
      router.push(`/login?next=${encodeURIComponent(href)}`);
    }
  }

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-6xl px-5 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10">
        <header className="flex flex-col gap-4 pb-5 sm:flex-row sm:items-center sm:justify-between sm:border-b sm:border-[var(--theme-border)]">
          <div className="min-w-0">
            <p className="hidden text-[0.68rem] font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase sm:block">
              Tinh Hoa Việt · Kết nối và sẻ chia
            </p>
            <h1 className="text-2xl font-semibold tracking-[-0.025em] text-[var(--theme-text)] sm:mt-1 sm:text-4xl">
              Cộng đồng
            </h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:mt-2">
              Nơi chia sẻ, trao đổi và kết nối những người quan tâm đến giá trị
              Việt.
            </p>
          </div>
          {authStatus === "authenticated" ? (
            <Link
              className="inline-flex min-h-11 w-fit shrink-0 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-5 text-sm font-semibold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href="/community/new"
            >
              + Viết bài
            </Link>
          ) : authStatus === "unauthenticated" ? (
            <Link
              className="inline-flex min-h-11 w-fit shrink-0 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-5 text-sm font-semibold text-[var(--theme-accent-contrast)] transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href={`/login?next=${encodeURIComponent("/community/new")}`}
            >
              Đăng nhập để viết bài
            </Link>
          ) : (
            <p className="text-sm text-[var(--theme-muted)]" role="status">
              {authStatus === "loading"
                ? "Đang xác minh tài khoản…"
                : "Không thể xác minh phiên. Thử tải lại trang."}
            </p>
          )}
        </header>

        {authStatus === "unauthenticated" ? (
          <p className="mt-3 border-l-2 border-[var(--theme-border)] pl-3 text-sm text-[var(--theme-muted)]">
            Bạn đang ở chế độ chỉ đọc. Đăng nhập để đăng bài, bình luận và tương
            tác.
          </p>
        ) : null}
        {authStatus === "error" ? (
          <p className="mt-3 text-sm text-[var(--theme-muted)]" role="alert">
            Không thể xác minh phiên. Nội dung vẫn ở chế độ đọc cho đến khi xác
            minh thành công.
          </p>
        ) : null}

        {categories.isError ? (
          <div className="mt-3 flex items-center gap-3 text-sm" role="alert">
            <p className="text-[var(--theme-muted)]">
              Chưa tải được danh sách chuyên mục.
            </p>
            <button
              className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              onClick={() => void categories.refetch()}
              type="button"
            >
              <RotateCcw aria-hidden="true" className="size-4" /> Thử lại
            </button>
          </div>
        ) : null}

        <form
          action="/community"
          aria-label="Tìm kiếm và lọc bài viết"
          className="mb-3 grid grid-cols-2 gap-2 sm:my-4 sm:grid-cols-[minmax(12rem,1fr)_minmax(10rem,15rem)_minmax(9rem,12rem)] sm:border-b sm:border-[var(--theme-border)] sm:pb-4"
          onSubmit={handleFilterSubmit}
          role="search"
        >
          <label className="relative col-span-2 flex min-w-0 items-center sm:col-span-1">
            <span className="sr-only">Tìm kiếm bài viết</span>
            <input
              className="min-h-11 min-w-0 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] py-2 pr-12 pl-3 text-sm text-[var(--theme-text)] outline-none focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20"
              defaultValue={q ?? ""}
              maxLength={120}
              name="q"
              placeholder="Tìm bài viết"
              type="search"
            />
            <button
              aria-label="Tìm bài viết"
              className="absolute right-1 inline-grid size-9 place-items-center rounded-md text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)] hover:text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              type="submit"
            >
              <Search aria-hidden="true" className="size-4" />
            </button>
          </label>
          <label className="sr-only" htmlFor="community-category-filter">
            Chuyên mục
          </label>
          <select
            className="min-h-11 min-w-0 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-2 text-sm text-[var(--theme-text)] outline-none focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20 sm:px-3"
            key={`${category ?? ""}:${sort}:${categories.data ? "ready" : "loading"}`}
            id="community-category-filter"
            name="category"
            defaultValue={category ?? ""}
            onChange={(event) => event.currentTarget.form?.requestSubmit()}
          >
            <option value="">Mọi chuyên mục</option>
            {categories.data?.map((item) => (
              <option key={item.id} value={item.slug}>
                {item.name}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="community-sort-filter">
            Sắp xếp
          </label>
          <select
            className="min-h-11 min-w-0 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-2 text-sm text-[var(--theme-text)] outline-none focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20 sm:px-3"
            key={`${category ?? ""}:${sort}`}
            id="community-sort-filter"
            name="sort"
            defaultValue={sort}
            onChange={(event) => event.currentTarget.form?.requestSubmit()}
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {relatedWorkId ? (
            <input name="relatedWorkId" type="hidden" value={relatedWorkId} />
          ) : null}
        </form>

        <section
          aria-label="Bài viết cộng đồng"
          aria-busy={
            needsAuthCheck || (!needsFollowingLogin && posts.isPending)
          }
          className="min-w-0"
        >
          {needsAuthCheck ? (
            <p className="my-5 text-sm text-[var(--theme-muted)]" role="status">
              {authStatus === "loading"
                ? "Đang xác định tài khoản để tải bài đang theo dõi…"
                : "Không thể xác minh phiên để tải bài đang theo dõi."}
            </p>
          ) : null}
          {needsFollowingLogin ? (
            <div
              className="my-5 border-l-2 border-[var(--theme-border)] py-1 pl-4"
              role="status"
            >
              <p className="font-bold text-[var(--theme-text)]">
                Đăng nhập để xem bài viết từ người bạn theo dõi.
              </p>
              <Link
                className="mt-3 inline-flex min-h-10 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                href={`/login?next=${encodeURIComponent(communityFeedHref({ category, q, sort, relatedWorkId }, page))}`}
              >
                Đăng nhập
              </Link>
            </div>
          ) : null}
          {!needsFollowingLogin && !needsAuthCheck && posts.isPending ? (
            <FeedSkeleton />
          ) : null}
          {!needsFollowingLogin && !needsAuthCheck && posts.isError ? (
            <div className="my-5 bg-[var(--theme-surface)] px-4 py-5 sm:px-6">
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
          {!needsFollowingLogin &&
          !needsAuthCheck &&
          posts.data?.data.length === 0 ? (
            <div className="my-5 rounded-xl bg-[var(--theme-surface)] px-4 py-8 text-center sm:py-10">
              <h2 className="text-xl font-bold text-[var(--theme-text)]">
                {category
                  ? "Chưa có bài viết trong chuyên mục này."
                  : "Chưa có bài viết nào."}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                Hãy bắt đầu bằng một câu chuyện hoặc ý tưởng của bạn.
              </p>
              {authStatus === "authenticated" ? (
                <Link
                  className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  href="/community/new"
                >
                  Viết bài đầu tiên
                </Link>
              ) : authStatus === "unauthenticated" ? (
                <Link
                  className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  href={`/login?next=${encodeURIComponent("/community/new")}`}
                >
                  Đăng nhập để viết bài đầu tiên
                </Link>
              ) : null}
            </div>
          ) : null}
          {!needsFollowingLogin &&
          !needsAuthCheck &&
          posts.data?.data.length ? (
            <>
              <div className="divide-y divide-[var(--theme-border)]">
                {posts.data.data.map((post) => (
                  <CommunityPostCard key={post.id} post={post} />
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
                      href={communityFeedHref(
                        { category, q, sort, relatedWorkId },
                        page - 1,
                      )}
                    >
                      <ArrowLeft aria-hidden="true" className="size-4" /> Trang
                      trước
                    </Link>
                  ) : (
                    <span />
                  )}
                  <p
                    aria-live="polite"
                    className="text-sm text-[var(--theme-muted)]"
                  >
                    Trang {page} / {totalPages}
                  </p>
                  {page < totalPages ? (
                    <Link
                      className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                      href={communityFeedHref(
                        { category, q, sort, relatedWorkId },
                        page + 1,
                      )}
                    >
                      Trang sau{" "}
                      <ArrowRight aria-hidden="true" className="size-4" />
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

const sortOptions: { value: CommunityPostSort; label: string }[] = [
  { value: "recent", label: "Mới nhất" },
  { value: "popular", label: "Nổi bật" },
  { value: "discussed", label: "Thảo luận nhiều" },
  { value: "following", label: "Đang theo dõi" },
];

function FeedSkeleton() {
  return (
    <div
      aria-label="Đang tải bài viết cộng đồng"
      className="py-4"
      role="status"
    >
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
