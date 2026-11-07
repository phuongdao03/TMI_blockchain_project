"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  LoaderCircle,
  Plus,
  RotateCcw,
  Search,
} from "lucide-react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityFeedHref } from "@/components/community/community-feed-url";
import { CommunityVipRooms } from "@/components/community/community-vip-rooms";
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
  const isPersonalizedFeed =
    sort === "following" || sort === "topics_following";
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
    enabled: !(isPersonalizedFeed && authStatus !== "authenticated"),
  });
  const needsFollowingLogin =
    isPersonalizedFeed && authStatus === "unauthenticated";
  const needsAuthCheck =
    isPersonalizedFeed &&
    (authStatus === "loading" || authStatus === "error");
  const total = posts.data?.meta.total ?? 0;
  const totalPages = Math.max(
    1,
    Math.ceil(total / (posts.data?.meta.pageSize || PAGE_SIZE)),
  );
  const categoryHref = (nextCategory?: string) =>
    communityFeedHref({ category: nextCategory, q, sort, relatedWorkId }, 1);

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>) {
    const data = new FormData(event.currentTarget);
    const selectedSort = data.get("sort");
    if (
      (selectedSort === "following" || selectedSort === "topics_following") &&
      authStatus === "unauthenticated"
    ) {
      event.preventDefault();
      const href = communityFeedHref(
        {
          category: String(data.get("category") || "") || undefined,
          q: String(data.get("q") || "") || undefined,
          sort: selectedSort,
          relatedWorkId,
        },
        1,
      );
      router.push(`/login?next=${encodeURIComponent(href)}`);
    }
  }

  return (
    <div className="public-theme-surface min-h-[calc(100dvh-5rem)]">
      <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 sm:py-9 lg:px-8 lg:py-12">
        <header className="flex flex-col gap-5 border-b border-[var(--theme-border)] pb-7 sm:flex-row sm:items-end sm:justify-between sm:pb-8">
          <div className="min-w-0">
            <p className="text-[0.68rem] font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">
              Tinh Hoa Việt · Kết nối và sẻ chia
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[-0.025em] text-[var(--theme-text)] sm:text-4xl">
              Cộng đồng Tinh Hoa Việt
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
              Nơi chia sẻ câu chuyện, kết nối con người và lan tỏa những giá trị
              Việt.
            </p>
          </div>
          {authStatus === "authenticated" ? (
            <Link
              className="inline-flex min-h-11 w-fit shrink-0 items-center justify-center gap-2 rounded-full bg-[var(--theme-accent)] px-5 text-sm font-semibold text-[var(--theme-accent-contrast)] transition-colors duration-150 hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href="/community/new"
            >
              <Plus aria-hidden="true" className="size-4" /> Viết bài
            </Link>
          ) : authStatus === "unauthenticated" ? (
            <Link
              className="inline-flex min-h-11 w-fit shrink-0 items-center justify-center gap-2 rounded-full bg-[var(--theme-accent)] px-5 text-sm font-semibold text-[var(--theme-accent-contrast)] transition-colors duration-150 hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              href={`/login?next=${encodeURIComponent("/community/new")}`}
            >
              <Plus aria-hidden="true" className="size-4" /> Đăng nhập để viết
              bài
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
          <p className="mt-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm leading-6 text-[var(--theme-muted)]">
            Bạn có thể xem nội dung công khai khi chưa đăng nhập. Đăng nhập để
            viết bài, bình luận hoặc theo dõi nội dung.
          </p>
        ) : null}
        {authStatus === "error" ? (
          <p
            className="mt-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm leading-6 text-[var(--theme-muted)]"
            role="alert"
          >
            Chưa thể xác minh trạng thái đăng nhập. Hãy tải lại trang để tiếp
            tục viết bài hoặc bình luận.
          </p>
        ) : null}

        <form
          action="/community"
          aria-label="Tìm kiếm và lọc bài viết"
          className="mt-6 flex flex-col gap-3 sm:flex-row"
          onSubmit={handleFilterSubmit}
          role="search"
        >
          <label className="relative flex min-w-0 flex-1 items-center">
            <span className="sr-only">Tìm kiếm bài viết</span>
            <input
              className="min-h-12 min-w-0 w-full rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] py-2 pr-12 pl-5 text-sm text-[var(--theme-text)] outline-none placeholder:text-[var(--theme-muted)] focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20"
              defaultValue={q ?? ""}
              maxLength={120}
              name="q"
              placeholder="Tìm kiếm bài viết..."
              type="search"
            />
            <button
              aria-label="Tìm bài viết"
              className="absolute right-1 inline-grid size-10 place-items-center rounded-full text-[var(--theme-muted)] transition-colors duration-150 hover:bg-[var(--theme-elevated)] hover:text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              type="submit"
            >
              <Search aria-hidden="true" className="size-4" />
            </button>
          </label>
          <label className="flex min-w-0 items-center sm:w-52">
            <span className="sr-only">Sắp xếp</span>
            <select
              className="min-h-12 min-w-0 w-full rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm text-[var(--theme-text)] outline-none focus-visible:border-[var(--theme-accent)] focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]/20"
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
          </label>
          {category ? (
            <input name="category" type="hidden" value={category} />
          ) : null}
          {relatedWorkId ? (
            <input name="relatedWorkId" type="hidden" value={relatedWorkId} />
          ) : null}
        </form>

        <nav
          aria-label="Danh mục bài viết cộng đồng"
          className="mb-8 sm:mb-10"
        >
          <ul className="flex flex-wrap gap-2 py-1">
            <li className="shrink-0">
              <Link
                aria-current={!category ? "page" : undefined}
                className={categoryPillClass(!category)}
                href={categoryHref(undefined)}
              >
                Tất cả
              </Link>
            </li>
            {categories.data?.map((item) => (
              <li className="shrink-0" key={item.id}>
                <Link
                  aria-current={category === item.slug ? "page" : undefined}
                  className={categoryPillClass(category === item.slug)}
                  href={categoryHref(item.slug)}
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {categories.isError ? (
          <div
            className="-mt-5 mb-6 flex items-center gap-3 text-sm"
            role="alert"
          >
            <p className="text-[var(--theme-muted)]">
              Chưa tải được danh sách chuyên mục.
            </p>
            <button
              className="inline-flex min-h-10 items-center gap-2 font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              onClick={() => void categories.refetch()}
              type="button"
            >
              <RotateCcw aria-hidden="true" className="size-4" /> Thử lại
            </button>
          </div>
        ) : null}

        <section
          aria-labelledby="community-posts-heading"
          aria-busy={
            needsAuthCheck || (!needsFollowingLogin && posts.isPending)
          }
          className="min-w-0"
        >
          <div className="mb-5 flex flex-wrap items-end justify-between gap-2">
            <h2
              className="text-xl font-semibold tracking-[-0.02em] text-[var(--theme-text)]"
              id="community-posts-heading"
            >
              Bài viết cộng đồng
            </h2>
            {posts.data ? (
              <p className="text-sm text-[var(--theme-muted)]">
                {total.toLocaleString("vi-VN")} bài viết
              </p>
            ) : null}
          </div>
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
                {sort === "topics_following"
                  ? "Đăng nhập để xem chủ đề bạn đang theo dõi."
                  : "Đăng nhập để xem bài viết từ người bạn theo dõi."}
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
            <div
              className="mx-auto my-5 max-w-2xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
              role="alert"
            >
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
            <div className="mx-auto my-5 max-w-2xl rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 py-8 text-center sm:py-10">
              <h2 className="text-xl font-bold text-[var(--theme-text)]">
                {q
                  ? "Chưa tìm thấy bài viết phù hợp."
                  : category
                    ? "Chưa có bài viết trong chuyên mục này."
                    : "Chưa có bài viết nào."}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                {q
                  ? "Thử một từ khóa khác hoặc xem lại toàn bộ bài viết."
                  : "Hãy bắt đầu bằng một câu chuyện hoặc ý tưởng của bạn."}
              </p>
              {q || category || relatedWorkId ? (
                <Link
                  className="mt-4 inline-flex min-h-11 items-center rounded-full border border-[var(--theme-border)] px-4 text-sm font-semibold text-[var(--theme-text)] transition-colors duration-150 hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  href="/community"
                >
                  Xóa bộ lọc
                </Link>
              ) : null}
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
              <div className="grid grid-cols-1 items-stretch gap-5 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3">
                {posts.data.data.map((post) => (
                  <CommunityPostCard key={post.id} post={post} />
                ))}
              </div>
              {totalPages > 1 ? (
                <nav
                  aria-label="Phân trang bài viết cộng đồng"
                  className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--theme-border)] py-5"
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
        <CommunityVipRooms />
      </div>
    </div>
  );
}

const sortOptions: { value: CommunityPostSort; label: string }[] = [
  { value: "recent", label: "Mới nhất" },
  { value: "popular", label: "Sôi nổi" },
  { value: "unanswered", label: "Chưa có trả lời" },
  { value: "discussed", label: "Thảo luận nhiều" },
  { value: "following", label: "Bài từ người bạn theo dõi" },
  { value: "topics_following", label: "Chủ đề đang theo dõi" },
];

function categoryPillClass(selected: boolean): string {
  const base =
    "inline-flex min-h-11 items-center justify-center rounded-full px-4 text-sm font-semibold transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]";
  return selected
    ? `${base} bg-[var(--theme-accent)] text-[var(--theme-accent-contrast)]`
    : `${base} bg-[var(--theme-elevated)] text-[var(--theme-text)] hover:bg-[var(--theme-border)]`;
}

function FeedSkeleton() {
  return (
    <div
      aria-label="Đang tải bài viết cộng đồng"
      className="grid grid-cols-1 gap-5 py-2 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3"
      role="status"
    >
      {Array.from({ length: 6 }, (_, index) => (
        <div
          aria-hidden="true"
          className="motion-safe:animate-pulse overflow-hidden rounded-[var(--radius-surface)] border border-[var(--theme-border)] bg-[var(--theme-surface)]"
          key={index}
        >
          <div className="aspect-[16/9] bg-[var(--theme-elevated)]" />
          <div className="p-4 sm:p-5">
            <div className="h-3 w-32 rounded bg-[var(--theme-elevated)]" />
            <div className="mt-4 h-6 w-4/5 rounded bg-[var(--theme-elevated)]" />
            <div className="mt-3 h-4 w-full rounded bg-[var(--theme-elevated)]" />
            <div className="mt-2 h-4 w-3/4 rounded bg-[var(--theme-elevated)]" />
            <div className="mt-6 h-10 rounded bg-[var(--theme-elevated)]" />
          </div>
        </div>
      ))}
      <span className="sr-only">
        <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />{" "}
        Đang tải
      </span>
    </div>
  );
}
