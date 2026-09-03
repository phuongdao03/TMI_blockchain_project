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
      <div
        aria-label="Đang tải bản đồ đề cử"
        className="public-theme-surface grid min-h-[30rem] place-items-center rounded-3xl border border-white/10 bg-ink-900 px-6 text-center"
        role="status"
      >
        <div>
          <LoaderCircle className="mx-auto size-8 animate-spin text-gold-300" />
          <p className="mt-4 text-sm text-slate-300">
            Đang tải các nội dung đã công bố theo khu vực…
          </p>
        </div>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div
        className="public-theme-surface grid min-h-[30rem] place-items-center rounded-3xl border border-white/10 bg-ink-900 px-6 text-center"
        role="alert"
      >
        <div className="max-w-md">
          <MapPin className="mx-auto size-10 text-primary-400" />
          <h2 className="mt-4 text-xl font-bold text-white">
            Chưa thể tải bản đồ đề cử
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Dữ liệu khu vực đang tạm thời gián đoạn. Vui lòng thử lại sau.
          </p>
          <button
            className="mt-5 min-h-11 rounded-xl border border-white/15 px-5 text-sm font-bold text-white transition-colors hover:bg-white/10"
            onClick={() => void query.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="public-theme-surface grid min-h-[30rem] overflow-hidden rounded-3xl border border-white/10 bg-ink-900 lg:grid-cols-[1fr_22rem]">
      <div className="relative overflow-hidden bg-[radial-gradient(circle_at_center,rgb(30_41_59),rgb(7_10_18)_70%)]">
        <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgb(148_163_184_/_15%)_1px,transparent_1px),linear-gradient(90deg,rgb(148_163_184_/_15%)_1px,transparent_1px)] [background-size:3rem_3rem]" />
        {query.data?.map((marker) => {
          const left = ((marker.longitude + 180) / 360) * 100;
          const top = ((90 - marker.latitude) / 180) * 100;
          return (
            <Link
              aria-label={marker.title}
              className="absolute z-10 -translate-x-1/2 -translate-y-1/2 text-primary-500 drop-shadow-[0_0_12px_rgb(239_68_68)]"
              href={`/works/${marker.slug}`}
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
                Chưa có nội dung công khai kèm vị trí để hiển thị trên bản đồ.
              </p>
            </div>
          </div>
        )}
      </div>
      <aside className="border-t border-white/10 p-5 lg:border-l lg:border-t-0">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
          Địa điểm đã công bố
        </p>
        <div className="mt-5 space-y-2">
          {query.data?.map((marker) => (
            <Link
              className="block rounded-xl border border-white/10 p-4 hover:bg-white/5"
              href={`/works/${marker.slug}`}
              key={marker.slug}
            >
              <p className="font-bold">{marker.title}</p>
              <p className="mt-1 text-xs text-slate-500">
                {marker.categoryName}
              </p>
            </Link>
          ))}
          {!query.data?.length && (
            <p className="rounded-xl border border-white/10 p-4 text-sm leading-6 text-slate-400">
              Danh sách sẽ xuất hiện khi nội dung công khai có thông tin vị trí.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
