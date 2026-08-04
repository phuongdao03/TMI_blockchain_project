import type { Metadata } from "next";

import {
  type CatalogParameters,
  PublicLibrary,
} from "@/components/public/public-library";
import type { PublicWorkSort } from "@/lib/api/types";
import { loadPublicCatalogInitialData } from "@/lib/api/public-catalog-server";

export const metadata: Metadata = {
  title: "Catalog tác phẩm công khai | TMI Certificate",
  description:
    "Khám phá các tác phẩm số đã được biên tập và công bố minh bạch trên nền tảng TMI Certificate.",
  alternates: { canonical: "/thu-vien" },
  openGraph: {
    type: "website",
    title: "Catalog tác phẩm công khai | TMI Certificate",
    description:
      "Khám phá các tác phẩm số đã được biên tập và công bố minh bạch trên nền tảng TMI Certificate.",
    url: "/thu-vien",
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
    <main className="relative isolate overflow-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[34rem] bg-[radial-gradient(circle_at_78%_8%,rgba(212,167,44,.12),transparent_24rem),radial-gradient(circle_at_10%_30%,rgba(220,38,38,.14),transparent_28rem)]" />
      <div className="mx-auto min-h-[calc(100dvh-5rem)] max-w-[90rem] px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
        <header className="grid gap-8 border-b border-white/10 pb-12 lg:grid-cols-[minmax(0,1fr)_23rem] lg:items-end">
          <div>
            <p className="text-xs font-bold tracking-[0.24em] text-gold-300 uppercase">TMI public catalog</p>
            <h1 className="mt-5 max-w-5xl text-4xl font-bold tracking-[-0.045em] text-white sm:text-6xl lg:text-7xl">
              Di sản được công bố.
              <span className="block text-slate-500">Giá trị được nhìn thấy.</span>
            </h1>
          </div>
          <div className="border-l border-gold-300/40 pl-5">
            <p className="text-sm leading-7 text-slate-400">
              Mỗi tác phẩm trong catalog là một projection công khai đã qua kiểm soát nội dung. Dữ liệu hồ sơ nội bộ và media nguồn luôn được tách biệt.
            </p>
          </div>
        </header>
        <div className="mt-10">
          <PublicLibrary {...parameters} initialData={initialData} />
        </div>
      </div>
    </main>
  );
}

function clean(value: string | undefined, maxLength: number): string | undefined {
  const normalized = value?.trim().slice(0, maxLength);
  return normalized || undefined;
}

function date(value: string | undefined): string | undefined {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined;
}

function sort(value: string | undefined): PublicWorkSort {
  return value === "featured" || value === "popular" ? value : "newest";
}
