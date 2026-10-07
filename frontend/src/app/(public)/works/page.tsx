import type { Metadata } from "next";
import { ArrowDown } from "lucide-react";

import {
  type CatalogParameters,
  PublicLibrary,
} from "@/components/public/public-library";
import type { PublicWorkSort } from "@/lib/api/types";
import { loadPublicCatalogInitialData } from "@/lib/api/public-catalog-server";
import { getServerAuthState } from "@/lib/auth/server-session";

export const metadata: Metadata = {
  title: "Danh sách đề cử",
  description:
    "Khám phá các đề cử đã được giới thiệu và công bố minh bạch trên Đề cử Tinh Hoa Việt.",
  alternates: { canonical: "/works" },
  openGraph: {
    type: "website",
    title: "Danh sách đề cử | Đề cử Tinh Hoa Việt",
    description:
      "Khám phá các đề cử đã được giới thiệu và công bố minh bạch trên Đề cử Tinh Hoa Việt.",
    url: "/works",
  },
};

export default async function LibraryPage({
  searchParams,
}: {
  searchParams: Promise<{
    query?: string;
    category?: string;
    tag?: string;
    publishedFrom?: string;
    publishedTo?: string;
    sort?: string;
    page?: string;
  }>;
}) {
  const input = await searchParams;
  const authState = await getServerAuthState();
  const embedded = Boolean(authState.user);
  const parameters: CatalogParameters = {
    query: clean(input.query, 120),
    category: clean(input.category, 160),
    tag: clean(input.tag, 160),
    publishedFrom: date(input.publishedFrom),
    publishedTo: date(input.publishedTo),
    sort: sort(input.sort),
    page: Math.max(1, Math.min(10_000, Number(input.page) || 1)),
  };
  const initialData = await loadPublicCatalogInitialData({
    ...parameters,
    pageSize: 12,
  });

  return (
    <div
      className={
        embedded
          ? "public-theme-surface public-library-page public-theme-surface--embedded overflow-hidden rounded-2xl px-4 py-6 sm:px-7 lg:px-9"
          : "public-theme-surface public-library-page overflow-hidden"
      }
    >
      <div
        className={
          embedded
            ? "mx-auto max-w-[90rem]"
            : "mx-auto min-h-[calc(100dvh-5rem)] max-w-[90rem] px-4 py-7 sm:px-6 sm:py-12 lg:px-8"
        }
      >
        <header
          className={`flex flex-col gap-4 border-b border-[var(--theme-border)] sm:flex-row sm:items-end sm:justify-between ${
            embedded ? "pb-5" : "pb-6 sm:pb-8"
          }`}
        >
          <div className="max-w-3xl">
            <p className="text-xs font-bold tracking-[0.2em] text-[var(--theme-accent)] uppercase">
              Khám phá Tinh Hoa Việt
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-[-0.035em] text-[var(--theme-text)] sm:text-5xl">
              Thư viện đề cử
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
              Khám phá tác phẩm, ý tưởng và câu chuyện đã được giới thiệu tới
              cộng đồng.
            </p>
          </div>
          <a
            className="inline-flex min-h-11 shrink-0 items-center gap-2 self-start rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] transition-colors hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] sm:self-auto"
            href="#catalog-search"
          >
            Tìm đề cử <ArrowDown aria-hidden="true" className="size-4" />
          </a>
        </header>
        <div className={embedded ? "mt-5 sm:mt-8" : "mt-6 sm:mt-9"}>
          <PublicLibrary {...parameters} initialData={initialData} />
        </div>
      </div>
    </div>
  );
}

function clean(
  value: string | undefined,
  maxLength: number,
): string | undefined {
  const normalized = value?.trim().slice(0, maxLength);
  return normalized || undefined;
}

function date(value: string | undefined): string | undefined {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined;
}

function sort(value: string | undefined): PublicWorkSort {
  return value === "featured" || value === "popular" ? value : "newest";
}
