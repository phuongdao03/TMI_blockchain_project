"use client";

import { ArrowUpRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { trackPublicCatalog } from "@/lib/analytics/public-catalog";
import type { PublicCatalogWork } from "@/lib/api/types";
import {
  cloudinaryPublicImageLoader,
  isCloudinaryPublicImage,
} from "@/lib/media/cloudinary-image-loader";
import {
  isPublicCoverImage,
  publicCoverLoader,
} from "@/lib/media/public-cover-loader";

const publishedDateFormatter = new Intl.DateTimeFormat("vi-VN", {
  month: "2-digit",
  year: "numeric",
});

export function PublicWorkCard({
  position,
  source,
  work,
}: {
  position: number;
  source: "featured" | "list";
  work: PublicCatalogWork;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const isLead = source === "featured" && position === 1;
  const variant = source === "list" ? "list" : isLead ? "lead" : "support";
  const imageUrl = work.thumbnailUrl;
  const usesResponsiveCover = isPublicCoverImage(imageUrl);
  const usesCloudinaryImage = isCloudinaryPublicImage(imageUrl);
  const hasImage = Boolean(imageUrl && imageUrl !== failedUrl);
  const published = publishedDateFormatter.format(new Date(work.publishedAt));

  return (
    <article
      className={"catalog-work-card catalog-work-card--" + variant}
      data-layout={
        variant === "list"
          ? "catalog-album-tile"
          : isLead
            ? "editorial-lead"
            : "editorial-support"
      }
    >
      <Link
        aria-label={"Xem đề cử " + work.title}
        className="catalog-work-card__link"
        href={"/works/" + encodeURIComponent(work.slug)}
        onClick={() =>
          trackPublicCatalog({
            name: "catalog_work_opened",
            properties: { position, slug: work.slug, source },
          })
        }
      >
        <div className="catalog-work-card__cover">
          {hasImage && imageUrl ? (
            <Image
              alt={work.thumbnailAltText || work.title}
              className="catalog-work-card__image"
              fetchPriority={isLead ? "high" : undefined}
              fill
              loading={isLead ? "eager" : "lazy"}
              loader={
                usesResponsiveCover
                  ? publicCoverLoader
                  : usesCloudinaryImage
                    ? cloudinaryPublicImageLoader
                    : undefined
              }
              onError={() => setFailedUrl(imageUrl)}
              sizes={
                isLead
                  ? "(max-width: 768px) 100vw, (max-width: 1280px) 80vw, 60vw"
                  : "(max-width: 640px) 100vw, (max-width: 1280px) 50vw, 33vw"
              }
              src={imageUrl}
              unoptimized={!usesResponsiveCover && !usesCloudinaryImage}
            />
          ) : (
            <div
              aria-label={"Bìa mặc định: " + work.title}
              className="catalog-work-card__fallback"
            >
              <span className="catalog-work-card__fallback-brand">
                Tinh Hoa Việt
              </span>
              <span aria-hidden="true" className="catalog-work-card__monogram">
                THV
              </span>
              <span className="catalog-work-card__fallback-index">
                {String(position).padStart(2, "0")}
              </span>
            </div>
          )}
          <span className="catalog-work-card__category">
            {work.categoryName}
          </span>
        </div>

        <div className="catalog-work-card__body">
          <div className="catalog-work-card__meta">
            {source === "featured" ? (
              <span className="catalog-work-card__kicker">Đề cử nổi bật</span>
            ) : null}
            <time dateTime={work.publishedAt}>{published}</time>
          </div>
          <h3 className="catalog-work-card__title">{work.title}</h3>
          <p className="catalog-work-card__description">
            {work.shortDescription}
          </p>
          <div className="catalog-work-card__footer">
            <span className="catalog-work-card__author">
              {work.authorDisplayName || "Tác giả được công bố"}
            </span>
            <span className="catalog-work-card__action">
              <span>{isLead ? "Xem đề cử" : "Khám phá"}</span>
              <ArrowUpRight aria-hidden="true" className="size-4" />
            </span>
          </div>
        </div>
      </Link>
    </article>
  );
}
