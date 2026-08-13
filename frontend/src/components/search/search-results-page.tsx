"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Filter,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { SearchAutocomplete } from "@/components/search/search-autocomplete";
import { RecentSearchHistory } from "@/components/search/recent-search-history";
import { SearchFilters } from "@/components/search/search-filters";
import { searchHref } from "@/components/search/search-url";
import { Button } from "@/components/ui/button";
import { publicApi } from "@/lib/api/client";
import type { SearchParameters, SearchResultWork } from "@/lib/api/types";

export function SearchResultsPage({
  parameters,
  authenticated = false,
}: {
  parameters: SearchParameters;
  authenticated?: boolean;
}) {
  const [filterOpen, setFilterOpen] = useState(false);
  const closeButton = useRef<HTMLButtonElement>(null);
  const results = useQuery({
    queryKey: ["public-search", parameters],
    queryFn: ({ signal }) => publicApi.search(parameters, signal),
  });
  const facetParameters = { ...parameters, cursor: undefined };
  const facets = useQuery({
    queryKey: ["public-search-facets", facetParameters],
    queryFn: ({ signal }) => publicApi.searchFacets(facetParameters, signal),
  });

  useEffect(() => {
    if (!filterOpen) return;
    closeButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFilterOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [filterOpen]);

  const activeFilters = activeFilterCount(parameters);
  return (
    <div>
      <Link
        className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-slate-400 transition hover:text-white"
        href="/works"
      >
        <ArrowLeft aria-hidden="true" className="size-4" /> Quay lại thư viện
      </Link>
      <header className="mt-7 max-w-4xl">
        <p className="text-xs font-bold tracking-[0.22em] text-gold-300 uppercase">
          TMI Search Index
        </p>
        <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] text-white sm:text-6xl">
          Tìm trong kho tài sản công khai.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">
          Tra cứu tác phẩm, danh mục, chủ đề và chứng thư trên tập dữ liệu đã
          được kiểm soát công khai.
        </p>
      </header>

      <form
        action="/search"
        className="mt-9 grid gap-3 border-y border-white/10 py-5 lg:grid-cols-[minmax(0,1fr)_13rem_auto]"
        method="get"
      >
        <SearchAutocomplete defaultValue={parameters.q} name="q" />
        <label>
          <span className="sr-only">Sắp xếp kết quả</span>
          <select
            className="min-h-12 w-full rounded-xl border border-white/10 bg-ink-950 px-4 text-sm text-white outline-none focus:border-gold-300"
            defaultValue={parameters.sort}
            name="sort"
          >
            <option value="relevance">Phù hợp nhất</option>
            <option value="newest">Mới nhất</option>
            <option value="oldest">Cũ nhất</option>
            <option value="most_viewed">Xem nhiều</option>
          </select>
        </label>
        <Button type="submit">
          <Search aria-hidden="true" className="size-4" /> Tìm kiếm
        </Button>
        {parameters.category ? (
          <input name="category" type="hidden" value={parameters.category} />
        ) : null}
        {parameters.tags.length ? (
          <input name="tags" type="hidden" value={parameters.tags.join(",")} />
        ) : null}
        {parameters.tagsMode !== "any" ? (
          <input name="tagsMode" type="hidden" value={parameters.tagsMode} />
        ) : null}
        {parameters.organization ? (
          <input
            name="organization"
            type="hidden"
            value={parameters.organization}
          />
        ) : null}
        {parameters.publishedFrom ? (
          <input
            name="publishedFrom"
            type="hidden"
            value={parameters.publishedFrom}
          />
        ) : null}
        {parameters.publishedTo ? (
          <input
            name="publishedTo"
            type="hidden"
            value={parameters.publishedTo}
          />
        ) : null}
        {parameters.hasBlockchainProof !== undefined ? (
          <input
            name="hasBlockchainProof"
            type="hidden"
            value={String(parameters.hasBlockchainProof)}
          />
        ) : null}
        {parameters.certificateStatus ? (
          <input
            name="certificateStatus"
            type="hidden"
            value={parameters.certificateStatus}
          />
        ) : null}
      </form>

      {authenticated ? (
        <RecentSearchHistory
          currentQuery={parameters.cursor ? undefined : parameters.q}
          resultsReady={results.isSuccess}
        />
      ) : null}

      <ActiveFilters facets={facets.data} parameters={parameters} />

      <div className="mt-8 grid gap-8 lg:grid-cols-[17rem_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <div className="sticky top-24 border-l border-white/10 pl-5">
            <SearchFilters facets={facets.data} parameters={parameters} />
          </div>
        </aside>
        <section aria-labelledby="search-results-heading" className="min-w-0">
          <div className="mb-5 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold tracking-[0.18em] text-primary-400 uppercase">
                Kết quả đã kiểm soát
              </p>
              <h2
                className="mt-2 text-2xl font-bold text-white"
                id="search-results-heading"
              >
                {parameters.q
                  ? `Kết quả cho “${parameters.q}”`
                  : "Khám phá mới nhất"}
              </h2>
            </div>
            <Button
              className="lg:hidden"
              onClick={() => setFilterOpen(true)}
              variant="outline"
            >
              <Filter aria-hidden="true" className="size-4" /> Bộ lọc{" "}
              {activeFilters ? `(${activeFilters})` : ""}
            </Button>
          </div>
          {results.isPending ? (
            <ResultsSkeleton />
          ) : results.error ? (
            <ErrorState retry={() => results.refetch()} />
          ) : !results.data.data.length ? (
            <EmptyState />
          ) : (
            <div className="divide-y divide-white/10 border-y border-white/10">
              {results.data.data.map((work, index) => (
                <SearchResult
                  key={work.id}
                  position={index + 1}
                  requestId={results.data.meta.requestId}
                  work={work}
                />
              ))}
            </div>
          )}
          {!results.isPending && results.data ? (
            <div
              aria-live="polite"
              className="mt-6 flex items-center justify-between gap-4 text-sm text-slate-500"
            >
              <span>
                {results.data.data.length} kết quả trên trang ·{" "}
                {results.data.meta.durationMs} ms
              </span>
              {results.data.meta.nextCursor ? (
                <Link
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-gold-300/30 px-4 font-semibold text-gold-200 transition hover:bg-gold-300/10"
                  href={searchHref({
                    ...parameters,
                    cursor: results.data.meta.nextCursor,
                  })}
                >
                  Trang tiếp{" "}
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Link>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>

      {filterOpen ? (
        <div
          aria-labelledby="search-filter-title"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm lg:hidden"
          role="dialog"
        >
          <div className="absolute inset-x-0 bottom-0 max-h-[92dvh] overflow-y-auto rounded-t-2xl border-t border-white/10 bg-ink-900 p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
            <div className="mb-6 flex items-center justify-between">
              <h2
                className="text-xl font-bold text-white"
                id="search-filter-title"
              >
                Bộ lọc tìm kiếm
              </h2>
              <button
                aria-label="Đóng bộ lọc"
                className="grid size-11 place-items-center rounded-lg border border-white/10 text-white"
                onClick={() => setFilterOpen(false)}
                ref={closeButton}
                type="button"
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>
            <SearchFilters facets={facets.data} parameters={parameters} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SearchResult({
  position,
  requestId,
  work,
}: {
  position: number;
  requestId: string;
  work: SearchResultWork;
}) {
  return (
    <article className="group grid gap-4 py-6 sm:grid-cols-[3rem_minmax(0,1fr)_auto] sm:items-start">
      <span className="font-mono text-sm tabular-nums text-slate-600">
        {String(position).padStart(2, "0")}
      </span>
      <div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>{work.categoryName}</span>
          <span aria-hidden="true">/</span>
          <time dateTime={work.publishedAt}>
            {new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(
              new Date(work.publishedAt),
            )}
          </time>
        </div>
        <h3 className="mt-2 text-xl font-bold tracking-tight text-white transition group-hover:text-gold-200">
          <Link
            href={`/works/${encodeURIComponent(work.slug)}`}
            onClick={() => {
              void publicApi
                .recordSearchClick(requestId, work.id)
                .catch(() => undefined);
            }}
          >
            {work.title}
          </Link>
        </h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          {work.shortDescription}
        </p>
        <p className="mt-3 text-sm text-slate-500">
          {work.authorDisplayName ?? "Tác giả chưa công bố"}
        </p>
      </div>
      {work.certificateNumber ? (
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-300">
          <BadgeCheck aria-hidden="true" className="size-4" />
          <span>{work.certificateNumber}</span>
        </div>
      ) : null}
    </article>
  );
}

function ActiveFilters({
  facets,
  parameters,
}: {
  facets?: Awaited<ReturnType<typeof publicApi.searchFacets>>;
  parameters: SearchParameters;
}) {
  const chips: Array<{ key: string; label: string; href: string }> = [];
  if (parameters.category)
    chips.push({
      key: "category",
      label:
        facets?.categories.find((item) => item.slug === parameters.category)
          ?.label ?? parameters.category,
      href: searchHref({
        ...parameters,
        category: undefined,
        cursor: undefined,
      }),
    });
  for (const tag of parameters.tags)
    chips.push({
      key: `tag-${tag}`,
      label: facets?.tags.find((item) => item.slug === tag)?.label ?? tag,
      href: searchHref({
        ...parameters,
        tags: parameters.tags.filter((item) => item !== tag),
        cursor: undefined,
      }),
    });
  if (parameters.organization)
    chips.push({
      key: "organization",
      label: `Tổ chức: ${parameters.organization}`,
      href: searchHref({
        ...parameters,
        organization: undefined,
        cursor: undefined,
      }),
    });
  if (parameters.publishedFrom)
    chips.push({
      key: "published-from",
      label: `Từ ${parameters.publishedFrom}`,
      href: searchHref({
        ...parameters,
        publishedFrom: undefined,
        cursor: undefined,
      }),
    });
  if (parameters.publishedTo)
    chips.push({
      key: "published-to",
      label: `Đến ${parameters.publishedTo}`,
      href: searchHref({
        ...parameters,
        publishedTo: undefined,
        cursor: undefined,
      }),
    });
  if (parameters.hasBlockchainProof !== undefined)
    chips.push({
      key: "proof",
      label: parameters.hasBlockchainProof
        ? "Đã có bằng chứng"
        : "Chưa có bằng chứng",
      href: searchHref({
        ...parameters,
        hasBlockchainProof: undefined,
        cursor: undefined,
      }),
    });
  if (parameters.certificateStatus)
    chips.push({
      key: "certificate",
      label: `Chứng thư: ${parameters.certificateStatus}`,
      href: searchHref({
        ...parameters,
        certificateStatus: undefined,
        cursor: undefined,
      }),
    });
  if (!chips.length) return null;
  return (
    <div className="mt-5 flex flex-wrap items-center gap-2">
      <span className="mr-1 text-xs font-semibold text-slate-500">
        Đang lọc
      </span>
      {chips.map((chip) => (
        <Link
          aria-label={`Bỏ ${chip.key === "category" ? "danh mục" : "bộ lọc"} ${chip.label}`}
          className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs font-semibold text-slate-200 hover:border-gold-300/30"
          href={chip.href}
          key={chip.key}
        >
          {chip.label}
          <X aria-hidden="true" className="size-3.5 text-slate-500" />
        </Link>
      ))}
    </div>
  );
}

function activeFilterCount(parameters: SearchParameters) {
  return (
    Number(Boolean(parameters.category)) +
    parameters.tags.length +
    Number(Boolean(parameters.organization)) +
    Number(Boolean(parameters.publishedFrom)) +
    Number(Boolean(parameters.publishedTo)) +
    Number(parameters.hasBlockchainProof !== undefined) +
    Number(Boolean(parameters.certificateStatus))
  );
}
function ResultsSkeleton() {
  return (
    <div
      aria-label="Đang tải kết quả"
      className="space-y-px border-y border-white/10"
    >
      {[0, 1, 2, 3].map((item) => (
        <div className="grid animate-pulse gap-3 py-7" key={item}>
          <div className="h-3 w-28 rounded bg-white/[0.05]" />
          <div className="h-6 w-2/3 rounded bg-white/[0.07]" />
          <div className="h-4 w-full rounded bg-white/[0.04]" />
        </div>
      ))}
    </div>
  );
}
function ErrorState({ retry }: { retry: () => void }) {
  return (
    <div className="border-y border-red-400/20 bg-red-400/[0.06] px-6 py-14 text-center">
      <p className="font-bold text-red-100">Chưa thể tải kết quả tìm kiếm</p>
      <p className="mt-2 text-sm text-red-200/70">
        Kết nối có thể đang gián đoạn. Bộ lọc trên URL vẫn được giữ nguyên.
      </p>
      <Button className="mt-5" onClick={retry}>
        <RotateCcw aria-hidden="true" className="size-4" /> Thử lại
      </Button>
    </div>
  );
}
function EmptyState() {
  return (
    <div className="border-y border-dashed border-white/15 px-6 py-16 text-center">
      <Search aria-hidden="true" className="mx-auto size-8 text-slate-600" />
      <h3 className="mt-4 text-xl font-bold text-white">
        Chưa có kết quả công khai phù hợp
      </h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
        Rút gọn từ khóa hoặc bỏ bớt điều kiện lọc để mở rộng phạm vi.
      </p>
      <Link
        className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-gold-200"
        href="/search"
      >
        Xóa bộ lọc
      </Link>
    </div>
  );
}
