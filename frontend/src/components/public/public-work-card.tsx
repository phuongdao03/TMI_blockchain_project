"use client";

import { ArrowUpRight, ImageOff, Sparkles } from "lucide-react";
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

  return (
    <article className="group relative flex min-w-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink-950">
      <Link
        aria-label={`Xem tác phẩm ${work.title}`}
        className="relative block aspect-[4/3] overflow-hidden bg-ink-800"
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
                className="absolute inset-0 animate-pulse bg-[linear-gradient(110deg,#141d2e_25%,#202c42_45%,#141d2e_65%)] bg-[length:200%_100%]"
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
          <span className="absolute inset-0 grid place-items-center bg-[radial-gradient(circle_at_70%_20%,rgba(212,167,44,.16),transparent_32%),linear-gradient(145deg,#141d2e,#070a12)]">
            <ImageOff aria-hidden="true" className="size-7 text-slate-600" />
          </span>
        )}
        <span className="absolute inset-0 bg-gradient-to-t from-ink-950 via-transparent to-transparent" />
        <span className="absolute top-4 left-4 rounded-full border border-white/15 bg-black/45 px-3 py-1 text-[0.68rem] font-bold tracking-[0.14em] text-white uppercase backdrop-blur">
          {work.categoryName}
        </span>
        {work.isFeatured ? (
          <span className="absolute top-4 right-4 grid size-9 place-items-center rounded-full bg-gold-300 text-ink-950">
            <Sparkles aria-label="Tác phẩm nổi bật" className="size-4" />
          </span>
        ) : null}
      </Link>

      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3 text-xs text-slate-500">
          <span className="font-mono">
            {String(position).padStart(2, "0")} / TMI
          </span>
          <time dateTime={work.publishedAt}>
            {new Intl.DateTimeFormat("vi-VN", {
              month: "2-digit",
              year: "numeric",
            }).format(new Date(work.publishedAt))}
          </time>
        </div>
        <h2 className="mt-5 line-clamp-2 text-xl font-bold tracking-tight text-white sm:text-2xl">
          {work.title}
        </h2>
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">
          {work.shortDescription}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {work.tags.slice(0, 3).map((tag) => (
            <span className="text-xs font-medium text-slate-500" key={tag.slug}>
              #{tag.name}
            </span>
          ))}
        </div>
        <div className="mt-auto flex items-end justify-between gap-4 pt-7">
          <p className="min-w-0 truncate text-sm font-semibold text-slate-300">
            {work.authorDisplayName || "Tác giả được công bố"}
          </p>
          <Link
            aria-label={`Mở chi tiết ${work.title}`}
            className="grid size-11 shrink-0 place-items-center rounded-full border border-white/15 text-white transition group-hover:border-gold-300 group-hover:text-gold-300"
            href={href}
            onClick={() =>
              trackPublicCatalog({
                name: "catalog_work_opened",
                properties: { position, slug: work.slug, source },
              })
            }
          >
            <ArrowUpRight className="size-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}
