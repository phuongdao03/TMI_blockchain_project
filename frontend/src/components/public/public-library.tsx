"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { PublicWorkCard } from "@/components/public/public-work-card";
import { SearchAutocomplete } from "@/components/search/search-autocomplete";
import { Button } from "@/components/ui/button";
import { trackPublicCatalog } from "@/lib/analytics/public-catalog";
import { publicApi } from "@/lib/api/client";
import type { PublicCatalogInitialData, PublicWorkSort } from "@/lib/api/types";
import { isPreviewRelease } from "@/lib/release-mode";

export interface CatalogParameters {
  query?: string;
  category?: string;
  tag?: string;
  publishedFrom?: string;
  publishedTo?: string;
  sort?: PublicWorkSort;
  page: number;
}

const controlClass =
  "min-h-12 w-full rounded-xl border border-white/10 bg-ink-950 px-4 text-sm text-white outline-none transition focus:border-gold-300 focus:ring-2 focus:ring-gold-300/20";

export function PublicLibrary({
  initialData,
  ...parameters
}: CatalogParameters & { initialData?: PublicCatalogInitialData }) {
  const [filterOpen, setFilterOpen] = useState(false);
  const preview = isPreviewRelease();
  const closeButton = useRef<HTMLButtonElement>(null);
  const filters = { ...parameters, pageSize: 12 };
  const works = useQuery({
    queryKey: ["public-catalog-works", filters],
    queryFn: () => publicApi.works(filters),
    initialData: initialData?.works,
    enabled: !preview,
  });
  const featured = useQuery({
    queryKey: ["public-catalog-featured"],
    queryFn: () => publicApi.featuredWorks(3),
    enabled: !preview && parameters.page === 1 && !hasFilters(parameters),
    initialData: initialData?.featured,
  });
  const categories = useQuery({
    queryKey: ["public-categories"],
    queryFn: publicApi.categories,
    enabled: !preview,
  });
  const tags = useQuery({
    queryKey: ["public-tags"],
    queryFn: publicApi.tags,
    enabled: !preview,
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

  const total = works.data?.meta.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 12));
  const activeFilterCount = countFilters(parameters);

  return (
    <div className="space-y-10">
      {featured.data?.length ? (
        <section aria-labelledby="featured-heading">
          <div className="mb-5 flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
                Tuyển chọn
              </p>
              <h2
                className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl"
                id="featured-heading"
              >
                Đề cử nổi bật
              </h2>
            </div>
            <span className="hidden text-sm text-slate-400 sm:block">
              Được biên tập theo thời hạn công bố
            </span>
          </div>
          <div
            className={
              featured.data.length > 1
                ? "grid gap-x-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,.65fr)]"
                : "max-w-5xl"
            }
          >
            {featured.data.map((work, index) => (
              <div className={index === 0 ? "lg:row-span-2" : ""} key={work.id}>
                <PublicWorkCard
                  position={index + 1}
                  source="featured"
                  work={work}
                />
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section aria-labelledby="catalog-results-heading">
        <div className="border-y border-white/10 py-5">
          <form
            className="flex flex-col gap-3 lg:flex-row"
            method="get"
            onSubmit={() =>
              trackPublicCatalog({
                name: "catalog_filter_applied",
                properties: {
                  activeFilterCount,
                  sort: parameters.sort ?? "newest",
                },
              })
            }
          >
            <SearchAutocomplete defaultValue={parameters.query} />
            <label className="min-w-48">
              <span className="sr-only">Sắp xếp</span>
              <select
                className={controlClass}
                defaultValue={parameters.sort ?? "newest"}
                name="sort"
              >
                <option value="newest">Mới công bố</option>
                <option value="featured">Nổi bật</option>
                <option value="popular">Được xem nhiều</option>
              </select>
            </label>
            <input
              name="category"
              type="hidden"
              value={parameters.category ?? ""}
            />
            <input name="tag" type="hidden" value={parameters.tag ?? ""} />
            <input
              name="publishedFrom"
              type="hidden"
              value={parameters.publishedFrom ?? ""}
            />
            <input
              name="publishedTo"
              type="hidden"
              value={parameters.publishedTo ?? ""}
            />
            <Button className="lg:px-6" type="submit">
              <Search className="size-4" /> Tìm kiếm
            </Button>
            <Button
              className="lg:hidden"
              onClick={() => setFilterOpen(true)}
              variant="outline"
            >
              <Filter className="size-4" /> Bộ lọc{" "}
              {activeFilterCount ? `(${activeFilterCount})` : ""}
            </Button>
          </form>
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <div aria-label="Bộ lọc kết quả" className="hidden lg:block">
            <div className="sticky top-24 border-l border-white/15 pl-5">
              <div className="flex items-center gap-2 text-white">
                <SlidersHorizontal className="size-4 text-gold-300" />
                <h2 className="font-bold">Tinh chỉnh kết quả</h2>
              </div>
              <FilterForm
                categories={categories.data ?? []}
                parameters={parameters}
                tags={tags.data ?? []}
              />
            </div>
          </div>

          <div className="min-w-0">
            <div className="mb-5 flex items-end justify-between gap-4">
              <div>
                <p className="text-xs font-bold tracking-[0.18em] text-primary-400 uppercase">
                  Danh sách đề cử
                </p>
                <h2
                  className="mt-2 text-2xl font-bold text-white"
                  id="catalog-results-heading"
                >
                  {activeFilterCount ? "Kết quả phù hợp" : "Mới được công bố"}
                </h2>
              </div>
              {!works.isPending && !works.error ? (
                <p aria-live="polite" className="text-sm text-slate-400">
                  {total.toLocaleString("vi-VN")} đề cử
                </p>
              ) : null}
            </div>

            {works.isPending ? (
              <CatalogSkeleton />
            ) : works.error ? (
              <div className="rounded-3xl border border-red-400/20 bg-red-400/10 px-6 py-14 text-center">
                <p className="font-bold text-red-100">
                  Chưa thể tải danh sách đề cử
                </p>
                <p className="mt-2 text-sm text-red-200/70">
                  Kết nối có thể đang gián đoạn. Bạn có thể thử lại mà không mất
                  bộ lọc.
                </p>
                <Button className="mt-5" onClick={() => works.refetch()}>
                  <RotateCcw className="size-4" /> Thử lại
                </Button>
              </div>
            ) : !works.data?.data.length ? (
              <div className="rounded-3xl border border-dashed border-white/15 px-6 py-16 text-center">
                <Search className="mx-auto size-8 text-slate-600" />
                <h3 className="mt-4 text-xl font-bold text-white">
                  Chưa tìm thấy đề cử phù hợp
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
                  Thử rút gọn từ khóa hoặc bỏ bớt điều kiện lọc.
                </p>
                <Link
                  className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-4 text-sm font-bold text-white"
                  href="/works"
                >
                  <X className="size-4" /> Xóa bộ lọc
                </Link>
              </div>
            ) : (
              <div className="border-y border-white/15">
                {works.data.data.map((work, index) => (
                  <PublicWorkCard
                    key={work.id}
                    position={(parameters.page - 1) * 12 + index + 1}
                    source="list"
                    work={work}
                  />
                ))}
              </div>
            )}

            {totalPages > 1 ? (
              <Pagination
                current={parameters.page}
                parameters={parameters}
                total={totalPages}
              />
            ) : null}
          </div>
        </div>
      </section>

      {filterOpen ? (
        <div
          aria-labelledby="mobile-filter-title"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm lg:hidden"
          role="dialog"
        >
          <div className="absolute inset-x-0 bottom-0 max-h-[90dvh] overflow-y-auto rounded-t-3xl border-t border-white/10 bg-ink-900 p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
            <div className="flex items-center justify-between">
              <h2
                className="text-xl font-bold text-white"
                id="mobile-filter-title"
              >
                Bộ lọc đề cử
              </h2>
              <button
                aria-label="Đóng bộ lọc"
                className="grid size-11 place-items-center rounded-full border border-white/10 text-white"
                onClick={() => setFilterOpen(false)}
                ref={closeButton}
                type="button"
              >
                <X className="size-5" />
              </button>
            </div>
            <FilterForm
              categories={categories.data ?? []}
              parameters={parameters}
              tags={tags.data ?? []}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function FilterForm({
  categories,
  parameters,
  tags,
}: {
  categories: Awaited<ReturnType<typeof publicApi.categories>>;
  parameters: CatalogParameters;
  tags: Awaited<ReturnType<typeof publicApi.tags>>;
}) {
  return (
    <form className="mt-5 space-y-5" method="get">
      <input name="query" type="hidden" value={parameters.query ?? ""} />
      <input name="sort" type="hidden" value={parameters.sort ?? "newest"} />
      <label className="block text-sm font-bold text-slate-300">
        Danh mục
        <select
          className={`${controlClass} mt-2`}
          defaultValue={parameters.category ?? ""}
          key={`${parameters.category}-${categories.length}`}
          name="category"
        >
          <option value="">Tất cả danh mục</option>
          {categories
            .filter((item) => item.slug)
            .map((item) => (
              <option key={item.id} value={item.slug!}>
                {item.name}
              </option>
            ))}
        </select>
      </label>
      <label className="block text-sm font-bold text-slate-300">
        Thẻ chủ đề
        <select
          className={`${controlClass} mt-2`}
          defaultValue={parameters.tag ?? ""}
          key={`${parameters.tag}-${tags.length}`}
          name="tag"
        >
          <option value="">Tất cả chủ đề</option>
          {tags
            .filter((item) => item.isActive)
            .map((item) => (
              <option key={item.id} value={item.slug}>
                {item.name}
              </option>
            ))}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm font-bold text-slate-300">
          Từ ngày
          <input
            className={`${controlClass} mt-2 px-3`}
            defaultValue={parameters.publishedFrom}
            name="publishedFrom"
            type="date"
          />
        </label>
        <label className="text-sm font-bold text-slate-300">
          Đến ngày
          <input
            className={`${controlClass} mt-2 px-3`}
            defaultValue={parameters.publishedTo}
            name="publishedTo"
            type="date"
          />
        </label>
      </div>
      <Button className="w-full" type="submit">
        <Filter className="size-4" /> Áp dụng bộ lọc
      </Button>
      {hasFilters(parameters) ? (
        <Link
          className="flex min-h-11 items-center justify-center gap-2 text-sm font-bold text-slate-400 hover:text-white"
          href="/works"
        >
          <X className="size-4" /> Xóa tất cả
        </Link>
      ) : null}
    </form>
  );
}

function CatalogSkeleton() {
  return (
    <div
      aria-label="Đang tải danh sách đề cử"
      className="divide-y divide-white/10 border-y border-white/10"
    >
      {Array.from({ length: 5 }, (_, index) => (
        <div
          className="grid animate-pulse grid-cols-[7rem_1fr] gap-4 py-5 sm:grid-cols-[9rem_1fr]"
          key={index}
        >
          <div className="aspect-square bg-ink-800 sm:aspect-[4/3]" />
          <div className="py-2">
            <div className="h-5 w-2/3 bg-ink-800" />
            <div className="mt-3 h-4 max-w-lg bg-ink-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

function Pagination({
  current,
  parameters,
  total,
}: {
  current: number;
  parameters: CatalogParameters;
  total: number;
}) {
  return (
    <nav
      aria-label="Phân trang đề cử"
      className="mt-8 flex items-center justify-between border-t border-white/10 pt-6"
    >
      <PageLink
        disabled={current <= 1}
        label="Trang trước"
        page={current - 1}
        parameters={parameters}
      >
        <ChevronLeft className="size-4" />
      </PageLink>
      <span className="text-sm text-slate-400">
        Trang <strong className="text-white">{current}</strong> / {total}
      </span>
      <PageLink
        disabled={current >= total}
        label="Trang sau"
        page={current + 1}
        parameters={parameters}
      >
        <ChevronRight className="size-4" />
      </PageLink>
    </nav>
  );
}

function PageLink({
  children,
  disabled,
  label,
  page,
  parameters,
}: {
  children: React.ReactNode;
  disabled: boolean;
  label: string;
  page: number;
  parameters: CatalogParameters;
}) {
  const href = catalogHref({ ...parameters, page });
  if (disabled)
    return (
      <span
        aria-disabled="true"
        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/5 px-4 text-sm text-slate-700"
      >
        {label}
        {children}
      </span>
    );
  return (
    <Link
      className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-4 text-sm font-bold text-white hover:border-gold-300"
      href={href}
      onClick={() =>
        trackPublicCatalog({
          name: "catalog_page_changed",
          properties: { page },
        })
      }
    >
      {page < parameters.page ? children : null}
      {label}
      {page > parameters.page ? children : null}
    </Link>
  );
}

function catalogHref(parameters: CatalogParameters): string {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(parameters)) {
    if (value && !(name === "page" && value === 1))
      query.set(name, String(value));
  }
  const suffix = query.toString();
  return suffix ? `/works?${suffix}` : "/works";
}

function countFilters(parameters: CatalogParameters): number {
  return [
    parameters.query,
    parameters.category,
    parameters.tag,
    parameters.publishedFrom,
    parameters.publishedTo,
  ].filter(Boolean).length;
}

function hasFilters(parameters: CatalogParameters): boolean {
  return (
    countFilters(parameters) > 0 ||
    (parameters.sort !== undefined && parameters.sort !== "newest")
  );
}
