import type { Metadata } from "next";

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
          ? "public-theme-surface public-library-page public-theme-surface--embedded relative isolate overflow-hidden rounded-2xl px-5 py-7 shadow-[0_24px_70px_rgba(15,23,42,.12)] sm:px-7 lg:px-9"
          : "public-theme-surface public-library-page relative isolate overflow-hidden"
      }
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[34rem] bg-[radial-gradient(circle_at_78%_8%,rgba(212,167,44,.12),transparent_24rem),radial-gradient(circle_at_10%_30%,rgba(220,38,38,.14),transparent_28rem)]"
      />
      <div
        className={
          embedded
            ? "mx-auto max-w-[90rem]"
            : "mx-auto min-h-[calc(100dvh-5rem)] max-w-[90rem] px-4 py-14 sm:px-6 lg:px-8 lg:py-20"
        }
      >
        <header
          className={`grid gap-6 border-b border-white/10 lg:grid-cols-[minmax(0,1fr)_23rem] lg:items-end ${
            embedded ? "pb-7" : "pb-12"
          }`}
        >
          <div>
            <p
              className={`text-xs font-bold tracking-[0.24em] uppercase ${
                embedded ? "text-gold-300" : "text-red-700"
              }`}
            >
              Không gian đề cử
            </p>
            <h1
              className={`mt-4 max-w-5xl font-bold tracking-[-0.045em] text-[var(--theme-text,#fff)] ${
                embedded
                  ? "text-3xl sm:text-4xl"
                  : "text-4xl sm:text-6xl lg:text-7xl"
              }`}
            >
              Thư viện đề cử
              {!embedded ? (
                <span className="block text-[var(--theme-muted,#94a3b8)]">
                  Những giá trị đáng được biết đến.
                </span>
              ) : null}
            </h1>
          </div>
          <div className="border-l border-gold-300/40 pl-5">
            <p className="text-sm leading-7 text-[var(--theme-muted,#94a3b8)]">
              Khám phá những nội dung đã được giới thiệu tới cộng đồng, với
              thông tin rõ ràng và dễ tra cứu.
            </p>
          </div>
        </header>
        <div
          className={
            embedded ? "mt-8" : "mt-10 px-5 py-8 sm:px-7 lg:px-9 lg:py-10"
          }
        >
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
