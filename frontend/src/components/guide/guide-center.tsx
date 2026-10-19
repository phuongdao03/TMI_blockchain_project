"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { guideApi } from "@/lib/api/client";
import type { CmsGuideArticle, CmsGuideAudience } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { getHighlightedSegments } from "@/components/guide/guide-search";

const PAGE_SIZE = 24;
const CATALOG_PAGE_SIZE = 100;
const EMPTY_ARTICLES: CmsGuideArticle[] = [];

const CATEGORY_LABELS: Record<string, string> = {
  "getting-started": "Bắt đầu",
  account: "Tài khoản",
  certificates: "Bằng xác lập",
  faq: "Câu hỏi thường gặp",
  dossiers: "Hồ sơ đề cử",
  reviews: "Thẩm định",
  "review-workflows": "Thẩm định",
  "employee-workflows": "Nhân sự",
  verification: "Xác minh",
  administration: "Quản trị",
};

const AUDIENCE_LABELS: Record<CmsGuideAudience, string> = {
  PUBLIC: "Mọi người",
  VIEWER: "Người tra cứu",
  USER: "Người gửi hồ sơ",
  MODERATOR: "Người kiểm duyệt",
  SUPER_ADMIN: "Quản trị viên",
  EMPLOYEE: "Nhân viên đã liên kết hồ sơ",
};

export function guideCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category.replaceAll("-", " ");
}

export function guideAudienceLabel(audience: CmsGuideAudience): string {
  return AUDIENCE_LABELS[audience];
}

export function GuideCenter({ scope }: { scope: "public" | "account" }) {
  const user = useAuthUser();
  const accessKey =
    scope === "account"
      ? `${user?.id ?? "signed-out"}:${user?.roles?.join(",") ?? ""}:${user?.isEmployee ? "employee" : "standard"}`
      : "public";
  const searchRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(draft.trim());
      setPage(1);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [draft]);

  useEffect(() => {
    function onGlobalKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onGlobalKeyDown);
    return () => window.removeEventListener("keydown", onGlobalKeyDown);
  }, []);

  useEffect(() => {
    const topic = new URLSearchParams(window.location.search).get("topic");
    if (!topic) return;
    const timer = window.setTimeout(() => setCategory(topic), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const catalog = useQuery({
    queryKey: ["guide-catalog", scope, accessKey],
    queryFn: () =>
      scope === "public"
        ? guideApi.publicList({ page: 1, pageSize: CATALOG_PAGE_SIZE })
        : guideApi.accessibleList({ page: 1, pageSize: CATALOG_PAGE_SIZE }),
  });
  const catalogArticles = catalog.data?.data ?? EMPTY_ARTICLES;
  const categoryOptions = useMemo(
    () =>
      [...new Set(catalogArticles.map((article) => article.category))].sort(
        (left, right) =>
          guideCategoryLabel(left).localeCompare(
            guideCategoryLabel(right),
            "vi",
          ),
      ),
    [catalogArticles],
  );
  const activeCategory = categoryOptions.includes(category) ? category : "";
  const listing = useQuery({
    queryKey: ["guide-center", scope, accessKey, query, activeCategory, page],
    queryFn: () => {
      const filters = {
        page,
        pageSize: PAGE_SIZE,
        query: query || undefined,
        category: activeCategory || undefined,
      };
      return scope === "public"
        ? guideApi.publicList(filters)
        : guideApi.accessibleList(filters);
    },
  });
  const articles = listing.data?.data ?? EMPTY_ARTICLES;
  const total = listing.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const basePath = scope === "public" ? "/guide" : "/help";
  const hrefFor = (article: CmsGuideArticle) => `${basePath}/${article.slug}`;

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(draft.trim());
    setPage(1);
  }

  function selectTopic(value: string) {
    setCategory(value);
    setPage(1);
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-7 text-[var(--theme-text)] sm:px-6 sm:py-9 lg:px-8">
      <header className="border-b border-[var(--theme-border)] pb-6">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Hướng dẫn sử dụng
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
          Tìm câu trả lời hoặc chọn một bài hướng dẫn bên dưới.
        </p>
        <form
          className="mt-5 flex w-full max-w-3xl gap-2"
          onSubmit={submitSearch}
          role="search"
        >
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Tìm trong hướng dẫn</span>
            <Search
              aria-hidden="true"
              className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-[var(--theme-muted)]"
            />
            <input
              className="min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] py-3 pl-10 pr-3 text-sm outline-none transition focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20"
              name="q"
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Tìm, ví dụ: gửi hồ sơ hoặc bằng xác lập"
              ref={searchRef}
              type="search"
              value={draft}
            />
          </label>
          <button
            className="min-h-12 rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-semibold text-[var(--theme-accent-contrast)] transition hover:brightness-95 focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)] focus:ring-offset-2"
            type="submit"
          >
            Tìm
          </button>
        </form>
      </header>

      <section
        aria-labelledby="guide-results-heading"
        className="mt-7"
        id="all-guides"
      >
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-bold" id="guide-results-heading">
              {query
                ? "Kết quả tìm kiếm"
                : activeCategory
                  ? guideCategoryLabel(activeCategory)
                  : "Tất cả hướng dẫn"}
            </h2>
            <p
              aria-live="polite"
              className="mt-1 text-sm text-[var(--theme-muted)]"
            >
              {listing.isPending ? "Đang tải hướng dẫn…" : `${total} bài viết`}
            </p>
          </div>
          <label className="flex items-center gap-3 text-sm font-semibold text-[var(--theme-muted)]">
            <span>Chủ đề</span>
            <select
              className="min-h-10 min-w-40 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)]"
              onChange={(event) => selectTopic(event.target.value)}
              value={activeCategory}
            >
              <option value="">Tất cả chủ đề</option>
              {categoryOptions.map((value) => (
                <option key={value} value={value}>
                  {guideCategoryLabel(value)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {listing.isError && (
          <div
            className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800"
            role="alert"
          >
            Không tải được hướng dẫn. Vui lòng tải lại trang hoặc thử lại sau.
          </div>
        )}
        {listing.isPending && (
          <p
            aria-live="polite"
            className="border-y border-[var(--theme-border)] py-6 text-sm text-[var(--theme-muted)]"
          >
            Đang tải các bài hướng dẫn…
          </p>
        )}
        {!listing.isPending && !listing.isError && articles.length === 0 && (
          <div className="border-y border-[var(--theme-border)] py-7">
            <h3 className="font-semibold">Không tìm thấy hướng dẫn</h3>
            <p className="mt-1 text-sm text-[var(--theme-muted)]">
              Thử từ khóa khác hoặc chọn một chủ đề khác.
            </p>
            {(query || activeCategory) && (
              <button
                className="mt-3 min-h-10 text-sm font-semibold text-[var(--theme-accent)] underline underline-offset-4 focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)]"
                onClick={() => {
                  setDraft("");
                  setQuery("");
                  setCategory("");
                  setPage(1);
                }}
                type="button"
              >
                Xóa bộ lọc
              </button>
            )}
          </div>
        )}
        {articles.length > 0 && (
          <ul className="divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)]">
            {articles.map((article) => (
              <li key={article.id}>
                <GuideTeaser
                  article={article}
                  href={hrefFor(article)}
                  query={query}
                />
              </li>
            ))}
          </ul>
        )}
        {pageCount > 1 && (
          <nav
            aria-label="Phân trang hướng dẫn"
            className="flex items-center justify-center gap-3 pt-2"
          >
            <button
              aria-label="Trang trước"
              className="inline-flex min-h-10 items-center gap-1 rounded-lg border border-[var(--theme-border)] px-3 text-sm disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              type="button"
            >
              <ChevronLeft aria-hidden="true" className="size-4" /> Trước
            </button>
            <span
              aria-live="polite"
              className="text-sm text-[var(--theme-muted)]"
            >
              Trang {page} / {pageCount}
            </span>
            <button
              aria-label="Trang sau"
              className="inline-flex min-h-10 items-center gap-1 rounded-lg border border-[var(--theme-border)] px-3 text-sm disabled:opacity-40"
              disabled={page >= pageCount}
              onClick={() => setPage((value) => value + 1)}
              type="button"
            >
              Tiếp <ChevronRight aria-hidden="true" className="size-4" />
            </button>
          </nav>
        )}
      </section>
    </div>
  );
}

function GuideTeaser({
  article,
  href,
  query = "",
}: {
  article: CmsGuideArticle;
  href: string;
  query?: string;
}) {
  return (
    <Link
      className="group flex min-w-0 items-start justify-between gap-4 py-4 transition-colors hover:bg-[var(--theme-elevated)]/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--theme-accent)] sm:px-3"
      href={href}
    >
      <div className="min-w-0">
        <div className="mb-1.5 flex flex-wrap items-center gap-x-2 text-xs text-[var(--theme-muted)]">
          <span className="font-semibold text-[var(--theme-accent)]">
            {guideCategoryLabel(article.category)}
          </span>
          <span aria-hidden="true">·</span>
          <span>{article.readingMinutes} phút đọc</span>
        </div>
        <h3 className="text-base font-semibold leading-6 group-hover:text-[var(--theme-accent)]">
          <HighlightedText query={query} text={article.title} />
        </h3>
        <p className="mt-1 line-clamp-2 text-sm leading-5 text-[var(--theme-muted)]">
          <HighlightedText query={query} text={article.summary} />
        </p>
      </div>
      <span
        aria-hidden="true"
        className="mt-5 shrink-0 text-[var(--theme-muted)] transition-transform group-hover:translate-x-1 group-hover:text-[var(--theme-accent)]"
      >
        →
      </span>
    </Link>
  );
}
function HighlightedText({ text, query }: { text: string; query: string }) {
  return (
    <>
      {getHighlightedSegments(text, query).map((segment, index) =>
        segment.matched ? (
          <mark
            className="rounded bg-amber-200/80 px-0.5 text-inherit"
            key={index}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </>
  );
}
