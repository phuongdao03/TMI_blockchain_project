"use client";

import { useQuery } from "@tanstack/react-query";
import { LoaderCircle, MapPin } from "lucide-react";
import Link from "next/link";

import { publicApi } from "@/lib/api/client";

export function PublicMap({ category }: { category?: string }) {
  const query = useQuery({
    queryKey: ["public-map", category],
    queryFn: () => publicApi.map(category),
  });
  if (query.isPending) {
    return (
      <LoaderCircle className="mx-auto mt-24 size-7 animate-spin text-gold-300" />
    );
  }
  return (
    <div className="grid min-h-[38rem] overflow-hidden rounded-3xl border border-white/10 bg-ink-900 lg:grid-cols-[1fr_22rem]">
      <div className="relative overflow-hidden bg-[radial-gradient(circle_at_center,rgb(30_41_59),rgb(7_10_18)_70%)]">
        <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgb(148_163_184_/_15%)_1px,transparent_1px),linear-gradient(90deg,rgb(148_163_184_/_15%)_1px,transparent_1px)] [background-size:3rem_3rem]" />
        {query.data?.map((marker) => {
          const left = ((marker.longitude + 180) / 360) * 100;
          const top = ((90 - marker.latitude) / 180) * 100;
          return (
            <Link
              aria-label={marker.title}
              className="absolute z-10 -translate-x-1/2 -translate-y-1/2 text-primary-500 drop-shadow-[0_0_12px_rgb(239_68_68)]"
              href={`/tai-san/${marker.slug}`}
              key={marker.slug}
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <MapPin className="size-8 fill-current" />
            </Link>
          );
        })}
        {!query.data?.length && (
          <div className="absolute inset-0 grid place-items-center px-6 text-center">
            <div>
              <MapPin className="mx-auto size-10 text-slate-600" />
              <p className="mt-4 max-w-sm text-sm leading-6 text-slate-400">
                Chưa có hồ sơ công khai chứa tọa độ địa lý trong bộ lọc này.
              </p>
            </div>
          </div>
        )}
      </div>
      <aside className="border-t border-white/10 p-5 lg:border-l lg:border-t-0">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
          Danh sách điểm
        </p>
        <div className="mt-5 space-y-2">
          {query.data?.map((marker) => (
            <Link
              className="block rounded-xl border border-white/10 p-4 hover:bg-white/5"
              href={`/tai-san/${marker.slug}`}
              key={marker.slug}
            >
              <p className="font-bold">{marker.title}</p>
              <p className="mt-1 text-xs text-slate-500">
                {marker.categoryName}
              </p>
            </Link>
          ))}
        </div>
      </aside>
    </div>
  );
}
