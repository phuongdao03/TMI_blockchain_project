"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, LoaderCircle } from "lucide-react";
import Link from "next/link";

import { publicApi } from "@/lib/api/client";

export function FeaturedAssets() {
  const query = useQuery({
    queryKey: ["public-featured-assets"],
    queryFn: () => publicApi.assets({ page: 1 }),
  });
  if (query.isPending) {
    return (
      <div className="grid min-h-52 place-items-center">
        <LoaderCircle className="size-6 animate-spin text-primary-700" />
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div className="border-y border-dashed border-neutral-300 px-6 py-12 text-center text-sm text-neutral-600">
        Tài sản tiêu biểu sẽ xuất hiện sau khi được công bố.
      </div>
    );
  }
  const featured = query.data.data.slice(0, 3);
  return (
    <div className="grid border-y border-neutral-300 md:grid-cols-3 md:divide-x md:divide-neutral-300">
      {featured.map((asset) => (
        <article
          className={`border-b border-neutral-300 py-7 last:border-b-0 md:border-b-0 md:px-7 first:md:pl-0 last:md:pr-0 ${featured.length === 1 ? "md:col-span-3" : ""}`}
          key={asset.slug}
        >
          <p className="text-xs font-bold uppercase tracking-wider text-primary-700">
            {asset.categoryName}
          </p>
          <h3 className="mt-4 text-xl font-bold text-neutral-950">
            {asset.title}
          </h3>
          <p className="mt-3 line-clamp-2 text-sm leading-6 text-neutral-600">
            {asset.summary}
          </p>
          <Link
            className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-primary-800"
            href={`/works/${asset.slug}`}
          >
            Xem thông tin <ArrowUpRight aria-hidden="true" className="size-4" />
          </Link>
        </article>
      ))}
    </div>
  );
}
