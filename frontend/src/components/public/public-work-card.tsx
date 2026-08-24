"use client";

import { ArrowUpRight, Sparkles } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { trackPublicCatalog } from "@/lib/analytics/public-catalog";
import type { PublicCatalogWork } from "@/lib/api/types";

export function PublicWorkCard({
  position,
  source,
  work,
}: {
  position: number;
  source: "featured" | "list";
  work: PublicCatalogWork;
}) {
  const [imageReady, setImageReady] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const href = `/works/${encodeURIComponent(work.slug)}`;
  const isLead = source === "featured" && position === 1;

  if (source === "list") {
    return (
      <article
        className="group min-w-0"
        data-layout="catalog-album-tile"
      >
        <Link
          aria-label={`Xem đề cử ${work.title}`}
          className="catalog-album-tile block overflow-hidden border border-white/15 bg-ink-900 transition hover:-translate-y-0.5 hover:border-gold-300/60 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold-300"
          href={href}
          onClick={() =>
            trackPublicCatalog({
              name: "catalog_work_opened",
              properties: { position, slug: work.slug, source },
            })
          }
        >
          <div className="relative aspect-[4/3] overflow-hidden bg-ink-800">
            {work.thumbnailUrl && !imageFailed ? (
              <>
                {!imageReady ? (
                  <span
                    aria-hidden="true"
                    className="absolute inset-0 animate-pulse bg-[linear-gradient(110deg,#3A1514_25%,#6E251E_45%,#3A1514_65%)] bg-[length:200%_100%]"
                    data-testid="image-loading"
                  />
                ) : null}
                <Image
                  alt={work.thumbnailAltText || work.title}
                  className={`object-cover transition duration-700 group-hover:scale-[1.04] ${imageReady ? "opacity-85" : "opacity-0"}`}
                  fill
                  onError={() => setImageFailed(true)}
                  onLoad={() => setImageReady(true)}
                  sizes="(max-width: 640px) 100vw, (max-width: 1280px) 50vw, 33vw"
                  src={work.thumbnailUrl}
                  unoptimized
                />
              </>
            ) : (
              <span className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(246,197,21,.2),transparent_32%),linear-gradient(145deg,#751C19,#240908)]" />
            )}
            <span className="absolute inset-0 bg-gradient-to-t from-ink-950/85 via-ink-950/5 to-transparent" />
            <span className="absolute top-3 left-3 border border-white/20 bg-ink-950/80 px-2.5 py-1 text-[0.6rem] font-bold tracking-[0.12em] text-white uppercase backdrop-blur">
              {work.categoryName}
            </span>
            <span className="absolute right-3 bottom-3 font-mono text-xs font-bold text-white/75">
              {String(position).padStart(2, "0")}
            </span>
          </div>
          <div className="min-w-0 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3 text-xs text-slate-400">
              <time dateTime={work.publishedAt}>
                {new Intl.DateTimeFormat("vi-VN", {
                  month: "2-digit",
                  year: "numeric",
                }).format(new Date(work.publishedAt))}
              </time>
              <span className="truncate">{work.authorDisplayName || "Tác giả công khai"}</span>
            </div>
            <h2 className="mt-3 line-clamp-2 text-xl font-bold tracking-[-0.025em] text-white transition-colors group-hover:text-gold-200">
              {work.title}
            </h2>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">
              {work.shortDescription}
            </p>
            <div className="mt-4 flex items-center justify-between gap-3">
              <div className="flex min-w-0 flex-wrap gap-x-2 gap-y-1 text-xs text-slate-400">
                {work.tags.slice(0, 2).map((tag) => (
                  <span key={tag.slug}>#{tag.name}</span>
                ))}
              </div>
              <ArrowUpRight
                aria-hidden="true"
                className="size-4 shrink-0 text-gold-300"
              />
            </div>
          </div>
        </Link>
      </article>
    );
  }

  const isFeaturedItem = true;
  const layout = isLead ? "editorial-lead" : "editorial-support";

  return (
    <article
      className={
        isLead
          ? "group grid min-w-0 gap-6 border-t border-white/15 pt-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,.85fr)]"
          : "group grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-4 border-t border-white/15 py-5 sm:grid-cols-[9rem_minmax(0,1fr)_auto] sm:items-center"
      }
      data-layout={layout}
    >
      <Link
        aria-label={`Xem đề cử ${work.title}`}
        className={`relative block overflow-hidden bg-ink-800 ${
          isLead ? "aspect-[16/10]" : "aspect-square sm:aspect-[4/3]"
        }`}
        href={href}
        onClick={() =>
          trackPublicCatalog({
            name: "catalog_work_opened",
            properties: { position, slug: work.slug, source },
          })
        }
      >
        {work.thumbnailUrl && !imageFailed ? (
          <>
            {!imageReady ? (
              <span
                aria-hidden="true"
                className="absolute inset-0 animate-pulse bg-[linear-gradient(110deg,#3A1514_25%,#6E251E_45%,#3A1514_65%)] bg-[length:200%_100%]"
                data-testid="image-loading"
              />
            ) : null}
            <Image
              alt={work.thumbnailAltText || work.title}
              className={`object-cover transition duration-700 group-hover:scale-[1.03] ${imageReady ? "opacity-80" : "opacity-0"}`}
              fill
              onError={() => setImageFailed(true)}
              onLoad={() => setImageReady(true)}
              sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
              src={work.thumbnailUrl}
              unoptimized
            />
          </>
        ) : (
          <span className="absolute inset-0 flex items-end overflow-hidden bg-[radial-gradient(circle_at_70%_20%,rgba(246,197,21,.2),transparent_32%),linear-gradient(145deg,#751C19,#240908)] p-5">
            <span
              aria-hidden="true"
              className="absolute -top-12 -right-8 font-mono text-[11rem] font-bold leading-none text-white/[0.035]"
            >
              {String(position).padStart(2, "0")}
            </span>
            <span className="relative font-mono text-[0.62rem] font-bold tracking-[0.16em] text-slate-400 uppercase">
              Hình ảnh đang cập nhật
            </span>
          </span>
        )}
        <span className="absolute inset-0 bg-gradient-to-t from-ink-950/80 via-transparent to-transparent" />
        <span className="absolute top-3 left-3 border border-white/20 bg-black/50 px-2.5 py-1 text-[0.6rem] font-bold tracking-[0.12em] text-white uppercase backdrop-blur">
          {work.categoryName}
        </span>
      </Link>

      <div className={isLead ? "flex flex-col py-1 xl:py-3" : "min-w-0"}>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
          <span className="font-mono">
            {String(position).padStart(2, "0")} / TMI
          </span>
          <span aria-hidden="true">—</span>
          <time dateTime={work.publishedAt}>
            {new Intl.DateTimeFormat("vi-VN", {
              month: "2-digit",
              year: "numeric",
            }).format(new Date(work.publishedAt))}
          </time>
        </div>
        {isFeaturedItem ? (
          <p className="mt-4 inline-flex items-center gap-2 text-[0.65rem] font-bold tracking-[0.16em] text-gold-300 uppercase">
            <Sparkles aria-hidden="true" className="size-3.5" /> Tuyển chọn
          </p>
        ) : null}
        <h2
          className={`line-clamp-2 font-bold tracking-[-0.025em] text-white transition-colors group-hover:text-gold-200 ${
            isLead ? "mt-3 text-3xl sm:text-4xl" : "mt-2 text-lg sm:text-xl"
          }`}
        >
          <Link
            href={href}
            onClick={() =>
              trackPublicCatalog({
                name: "catalog_work_opened",
                properties: { position, slug: work.slug, source },
              })
            }
          >
            {work.title}
          </Link>
        </h2>
        <p
          className={`mt-3 text-sm leading-6 text-slate-400 ${
            isLead ? "line-clamp-3 max-w-xl" : "line-clamp-2"
          }`}
        >
          {work.shortDescription}
        </p>
        <div className={`flex flex-wrap gap-2 ${isLead ? "mt-5" : "mt-3"}`}>
          {work.tags.slice(0, 3).map((tag) => (
            <span className="text-xs font-medium text-slate-400" key={tag.slug}>
              #{tag.name}
            </span>
          ))}
        </div>
        <div
          className={`flex items-center justify-between gap-4 ${
            isLead ? "mt-auto pt-8" : "pt-4"
          }`}
        >
          <p className="min-w-0 truncate text-sm font-semibold text-slate-300">
            {work.authorDisplayName || "Tác giả được công bố"}
          </p>
          {isLead ? (
            <Link
              aria-label={`Mở chi tiết ${work.title}`}
              className="inline-flex min-h-11 shrink-0 items-center gap-2 text-sm font-bold text-white transition group-hover:text-gold-300"
              href={href}
              onClick={() =>
                trackPublicCatalog({
                  name: "catalog_work_opened",
                  properties: { position, slug: work.slug, source },
                })
              }
            >
              <span className="hidden sm:inline">Xem chi tiết</span>
              <ArrowUpRight aria-hidden="true" className="size-4" />
            </Link>
          ) : null}
        </div>
      </div>
      {!isLead ? (
        <Link
          aria-label={`Mở chi tiết ${work.title}`}
          className="hidden size-11 place-items-center self-center border border-white/15 text-white transition hover:border-gold-300 hover:text-gold-300 sm:grid"
          href={href}
          onClick={() =>
            trackPublicCatalog({
              name: "catalog_work_opened",
              properties: { position, slug: work.slug, source },
            })
          }
        >
          <ArrowUpRight aria-hidden="true" className="size-4" />
        </Link>
      ) : null}
    </article>
  );
}
