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
        <LoaderCircle className="size-6 animate-spin text-gold-300" />
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div className="rounded-3xl border border-dashed border-white/15 px-6 py-12 text-center text-sm text-slate-400">
        Tài sản tiêu biểu sẽ xuất hiện sau khi được công bố.
      </div>
    );
  }
  const featured = query.data.data.slice(0, 3);
  return (
    <div className="grid gap-px overflow-hidden rounded-3xl border border-white/10 bg-white/10 md:grid-cols-3">
      {featured.map((asset) => (
        <article
          className={`bg-ink-950 p-6 ${featured.length === 1 ? "md:col-span-3" : ""}`}
          key={asset.slug}
        >
          <p className="text-xs font-bold uppercase tracking-wider text-gold-300">
            {asset.categoryName}
          </p>
          <h3 className="mt-4 text-xl font-bold text-white">{asset.title}</h3>
          <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">
            {asset.summary}
          </p>
          <Link className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-white" href={`/tai-san/${asset.slug}`}>
            Xem bằng chứng <ArrowUpRight className="size-4" />
          </Link>
        </article>
      ))}
    </div>
  );
}
